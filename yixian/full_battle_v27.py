"""Source-scoped seasonal opening and formation hooks; frozen v26 retained."""
from copy import deepcopy
import hashlib,json,shutil,subprocess
from pathlib import Path
from . import full_battle_v26 as v26
from .simulator import engine_contract,SimulatorError
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-season-context-v27.json'
PROOF_SHA='44d5f4877bd6ebe38923f1268c78aa72d24e5d43f0679fa653791e5714b5fe22'
BRIDGE=ROOT/'tools/full_battle_bridge_v27.mjs'
UnresolvedBattle=v26.UnresolvedBattle
catalogue=v26.catalogue
derive_start_initiative=v26.derive_start_initiative

def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Season context evidence changed')
    facts=json.loads(raw)
    for p,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('Season context source changed:'+p)
    return facts

def compile_start(row,**kwargs):
    extension_contract();projected=deepcopy(row);entries=[]
    for player in projected['players']:
        start=player['candidate_start'];choices=start.get('xian_mo_strategies')
        if not isinstance(choices,list) or any(type(x) is not int for x in choices):
            raise UnresolvedBattle('Explicit xian_mo_strategies array required')
        owned=[x for x in choices if x in (3001,23080)]
        if len(set(owned))!=len(owned):raise UnresolvedBattle('Duplicate season context ownership')
        entries.append(owned);start['xian_mo_strategies']=[x for x in choices if x not in owned]
    result=v26.compile_start(projected,**kwargs)
    if any(entries):
        result['battle']['season_current_context']={'players':entries}
        for i,source in enumerate(row['players']):
            result['effect_players'][i]['season_choices']=deepcopy(source['candidate_start']['xian_mo_strategies'])
            if entries[i]:result['declared_components'][i]['season_context_v27']={
                'ids':entries[i],'evidence_sha256':PROOF_SHA,'acquisition_rewards_reapplied':False,
                'training_label_allowed':False}
    return result

def simulate_batch(battles,*,timeout=90):
    extension_contract()
    # Check the existing complete chain without executing an old bridge.
    v26.extension_contract();v26.v25.extension_contract();v26.v24.extension_contract()
    v26.v23.extension_contract();v26.v22.extension_contract();v26.v17.extension_contract()
    module=v26.v17.v16
    for attr in ['v15','v14','v13','v12','v11','v10','v9','v8','v7','v6','v5']:
        module.extension_contract();module=getattr(module,attr)
    module.extension_contract();module.v4.plant_contract();module.v4.v3.counter_contract();module.v4.v3.v2.extension_contract()
    if not isinstance(battles,list) or not 1<=len(battles)<=1000:raise ValueError('Require1–1000 battles')
    node=shutil.which('node')
    if not node:raise SimulatorError('Node runtime is not on PATH')
    run=subprocess.run([node,'--experimental-default-type=module',str(BRIDGE)],
        input=json.dumps(battles,ensure_ascii=False,allow_nan=False),text=True,encoding='utf8',
        cwd=ROOT,capture_output=True,timeout=timeout)
    if run.returncode:raise SimulatorError(run.stderr.strip())
    results=json.loads(run.stdout)
    if len(results)!=len(battles):raise SimulatorError('Batch result count mismatch')
    return {'results':results,'engine':engine_contract(),'adapter_contract':{'schema':'complete-single-battle-diagnostic-v27',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),'current_server_verified':False,'training_label_allowed':False}
