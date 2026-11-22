"""Current spirit outburst and timed overheal damage; frozen v29 retained."""
from copy import deepcopy
import hashlib,json,shutil,subprocess
from pathlib import Path
from . import full_battle_v29 as v29
from .simulator import engine_contract,SimulatorError
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-spirit-outburst-v30.json'
PROOF_SHA='783658033e37aff9f76100add82cbfc30c1fdebedb89a9aab27593f3057a1089'
BRIDGE=ROOT/'tools/full_battle_bridge_v30.mjs'
UnresolvedBattle=v29.UnresolvedBattle
derive_start_initiative=v29.derive_start_initiative

def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Spirit outburst evidence changed')
    facts=json.loads(raw)
    for p,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('Spirit outburst source changed:'+p)
    return facts

def catalogue():
    facts=extension_contract();cards,mapping,talents,season=v29.catalogue()
    for family in facts['families']:
        for card,alias in zip(family['cards'],family['runtime_ids']):
            if card['id'] in mapping or alias in mapping.values():raise UnresolvedBattle('Spirit outburst alias collision')
            mapping[card['id']]=alias
    return cards,mapping,talents,season

def compile_start(row,**kwargs):
    extension_contract()
    if 'tables' not in kwargs:kwargs['tables']=catalogue()
    return v29.compile_start(row,**kwargs)


def simulate_batch(battles,*,timeout=90):
    extension_contract();v29.extension_contract()
    v28=v29.v28
    v28.extension_contract()
    v27=v28.v27
    v26=v27.v26
    v27.extension_contract()
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
    return {'results':results,'engine':engine_contract(),'adapter_contract':{'schema':'complete-single-battle-diagnostic-v30',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),'current_server_verified':False,'training_label_allowed':False}
