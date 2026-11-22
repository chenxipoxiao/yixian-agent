"""Current wind cards and the official battle limit over the frozen v7 engine."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from . import full_battle_v7 as v7
from .simulator import engine_contract, SimulatorError

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-wind-cards-v8.json'
PROOF_SHA='ad4cdfdadce2a3d4d7e540bee184f0d76b10c9096eea4c472468b058d9bf01c4'
BRIDGE=ROOT/'tools/full_battle_bridge_v8.mjs'
UnresolvedBattle=v7.UnresolvedBattle
catalogue=v7.catalogue
derive_start_initiative=v7.derive_start_initiative

def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Current state evidence changed')
    facts=json.loads(raw)
    for path,key in [('data/local/2026-11-06/tables/CardConfig.json','card_table_sha256'),('external/yisim/gamestate_full.js','native_engine_sha256')]:
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=facts[key]:raise UnresolvedBattle('Current wind source changed:'+path)
    return facts

def compile_start(row,**kwargs):
    extension_contract()
    result=v7.compile_start(row,**kwargs)
    result['battle']['current_rules_context']={'realms':[p['candidate_start']['level'] for p in row['players']]}
    result['current_wind_patch']={'evidence_sha256':PROOF_SHA,'official_turn_limit':64,'training_label_allowed':False}
    return result

def simulate_batch(battles,*,timeout=90):
    extension_contract();v7.extension_contract();v7.v6.extension_contract();v7.v6.v5.extension_contract()
    v7.v6.v5.v4.plant_contract();v7.v6.v5.v4.v3.counter_contract();v7.v6.v5.v4.v3.v2.extension_contract()
    engine=engine_contract()
    if not isinstance(battles,list) or not battles or len(battles)>1000:raise ValueError('Require 1–1000 battles')
    node=shutil.which('node')
    if not node:raise SimulatorError('Node runtime is not on PATH')
    run=subprocess.run([node,'--experimental-default-type=module',str(BRIDGE)],
        input=json.dumps(battles,ensure_ascii=False,allow_nan=False),text=True,encoding='utf-8',cwd=ROOT,capture_output=True,timeout=timeout)
    if run.returncode:raise SimulatorError(run.stderr.strip())
    results=json.loads(run.stdout)
    if len(results)!=len(battles):raise SimulatorError('Batch result count mismatch')
    return {'results':results,'engine':engine,'adapter_contract':{'schema':'complete-single-battle-diagnostic-v8',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'old_versions_unchanged':True,
        'full_match_environment':False,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),
        'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'current_server_verified':False,'training_label_allowed':False}
