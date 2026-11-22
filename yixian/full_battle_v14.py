"""Current hidden-dragon and elbow-strike cards over the frozen v10 engine."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from . import full_battle_v13 as v13
v10=v13.v12.v11.v10
v9=v10.v9
from .simulator import engine_contract, SimulatorError
v8=v9.v8
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-animal-cards-v14.json'
PROOF_SHA='7ca841c61895fb0bfaedf52b6272ac5232df00bfa58a75a8b698b9c5de6d0bb2'
BRIDGE=ROOT/'tools/full_battle_bridge_v14.mjs'
UnresolvedBattle=v9.UnresolvedBattle
def catalogue():
    facts=extension_contract();cards,mapping,talents,season=v13.catalogue()
    for f in facts['families']:
        for c,alias in zip(f['cards'],f['runtime_ids']):
            if c['id'] in mapping or alias in mapping.values():raise UnresolvedBattle('Chain card alias already assigned')
            mapping[c['id']]=alias
    return cards,mapping,talents,season
derive_start_initiative=v13.derive_start_initiative

def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Chain card evidence changed')
    facts=json.loads(raw)
    for path,digest in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise UnresolvedBattle('Chain card source changed:'+path)
    return facts

def compile_start(row,**kwargs):
    extension_contract()
    if 'tables' not in kwargs:kwargs['tables']=catalogue()
    result=v13.compile_start(row,**kwargs)
    result['current_animal_cards']={'evidence_sha256':PROOF_SHA,'training_label_allowed':False}
    return result

def simulate_batch(battles,*,timeout=90):
    extension_contract();v13.extension_contract();v13.v12.extension_contract();v13.v12.v11.extension_contract();v10.extension_contract();v9.extension_contract();v8.extension_contract();v8.v7.extension_contract();v8.v7.v6.extension_contract();v8.v7.v6.v5.extension_contract()
    v8.v7.v6.v5.v4.plant_contract();v8.v7.v6.v5.v4.v3.counter_contract();v8.v7.v6.v5.v4.v3.v2.extension_contract()
    engine=engine_contract()
    if not isinstance(battles,list) or not battles or len(battles)>1000:raise ValueError('Require 1–1000 battles')
    node=shutil.which('node')
    if not node:raise SimulatorError('Node runtime is not on PATH')
    run=subprocess.run([node,'--experimental-default-type=module',str(BRIDGE)],
        input=json.dumps(battles,ensure_ascii=False,allow_nan=False),text=True,encoding='utf-8',cwd=ROOT,capture_output=True,timeout=timeout)
    if run.returncode:raise SimulatorError(run.stderr.strip())
    results=json.loads(run.stdout)
    if len(results)!=len(battles):raise SimulatorError('Batch result count mismatch')
    return {'results':results,'engine':engine,'adapter_contract':{'schema':'complete-single-battle-diagnostic-v14',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'old_versions_unchanged':True,
        'full_match_environment':False,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),
        'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'current_server_verified':False,'training_label_allowed':False}
