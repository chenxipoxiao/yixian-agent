"""Current Full Moon Flying Shadow over frozen prior battle contracts."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from . import full_battle_v23 as v23, full_battle_v22 as v22, full_battle_v17 as v17
from .simulator import engine_contract, SimulatorError
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-full-moon-v24.json'
PROOF_SHA='58c7c9b199ba8dd5fea4c9cfad88c059ba9de43ecf4985ccb74ad4ddb7cc5deb'
BRIDGE=ROOT/'tools/full_battle_bridge_v24.mjs'
UnresolvedBattle=v23.UnresolvedBattle
catalogue=v23.catalogue
derive_start_initiative=v23.derive_start_initiative

def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Full Moon evidence changed')
    facts=json.loads(raw)
    for p,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('Full Moon source changed:'+p)
    return facts

def compile_start(row,**kwargs):
    extension_contract();projected=deepcopy(row);entries=[]
    for player in projected['players']:
        start=player['candidate_start'];choices=start.get('xian_mo_strategies')
        if not isinstance(choices,list) or any(type(x) is not int for x in choices):
            raise UnresolvedBattle('Explicit xian_mo_strategies array required')
        if 7065 in choices:
            if choices.count(7065)!=1:raise UnresolvedBattle('Duplicate Full Moon strategy7065')
            start['xian_mo_strategies']=[x for x in choices if x!=7065]
            entries.append([7065])
        else:entries.append([])
    result=v23.compile_start(projected,**kwargs)
    if any(entries):
        result['battle']['season_full_moon']={'players':entries}
        for index,(source,effect) in enumerate(zip(row['players'],result['effect_players'])):
            effect['season_choices']=deepcopy(source['candidate_start']['xian_mo_strategies'])
            if entries[index]:
                result['declared_components'][index]['full_moon']={'strategy_id':7065,
                    'agility_threshold':9,'agility_cost':9,'evidence_sha256':PROOF_SHA,
                    'acquisition_reward_reapplied':False,'training_label_allowed':False}
    return result

def simulate_batch(battles,*,timeout=90):
    extension_contract();v23.extension_contract();v22.extension_contract();v17.extension_contract()
    v17.v16.extension_contract();v17.v16.v15.extension_contract();v17.v16.v15.v14.extension_contract()
    v17.v16.v15.v14.v13.extension_contract();v17.v16.v15.v14.v13.v12.extension_contract()
    module=v17.v16.v15.v14.v13.v12.v11
    for attr in ['v10','v9','v8','v7','v6','v5']:
        module.extension_contract();module=getattr(module,attr)
    module.extension_contract();module.v4.plant_contract();module.v4.v3.counter_contract();module.v4.v3.v2.extension_contract()
    if not isinstance(battles,list) or not 1<=len(battles)<=1000:raise ValueError('Require 1–1000 battles')
    node=shutil.which('node')
    if not node:raise SimulatorError('Node runtime is not on PATH')
    run=subprocess.run([node,'--experimental-default-type=module',str(BRIDGE)],input=json.dumps(battles,ensure_ascii=False,allow_nan=False),
        text=True,encoding='utf-8',cwd=ROOT,capture_output=True,timeout=timeout)
    if run.returncode:raise SimulatorError(run.stderr.strip())
    results=json.loads(run.stdout)
    if len(results)!=len(battles):raise SimulatorError('Batch result count mismatch')
    return {'results':results,'engine':engine_contract(),'adapter_contract':{'schema':'complete-single-battle-diagnostic-v24',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),'current_server_verified':False,'training_label_allowed':False}
