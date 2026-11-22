"""Delayed per-card and next-attack effects over frozen v16."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from . import full_battle_v16 as v16
from .simulator import engine_contract, SimulatorError

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-delayed-effects-v17.json'
PROOF_SHA='2cb785a17ffe524303bc5360f3e738f15b3f9ff6f3aa1ea6a83d44e3aa049829'
BRIDGE=ROOT/'tools/full_battle_bridge_v17.mjs'
UnresolvedBattle=v16.UnresolvedBattle
def catalogue():
    facts=extension_contract();cards,mapping,talents,season=v16.catalogue()
    for family in facts['families']:
        for card,alias in zip(family['cards'],family['runtime_ids']):
            if card['id'] in mapping or alias in mapping.values():raise UnresolvedBattle('Season card alias collision')
            mapping[card['id']]=alias
    return cards,mapping,talents,season

derive_start_initiative=v16.derive_start_initiative


def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Season card evidence changed')
    facts=json.loads(raw)
    for path,digest in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:
            raise UnresolvedBattle('Season card source changed:'+path)
    return facts


def compile_start(row,**kwargs):
    extension_contract()
    if 'tables' not in kwargs:kwargs['tables']=catalogue()
    result=v16.compile_start(row,**kwargs)
    result['current_delayed_effects']={'evidence_sha256':PROOF_SHA,'training_label_allowed':False}
    return result


def simulate_batch(battles,*,timeout=90):
    extension_contract();v16.extension_contract();v16.v15.extension_contract();v16.v15.v14.extension_contract();v16.v15.v14.v13.extension_contract();v16.v15.v14.v13.v12.extension_contract()
    module=v16.v15.v14.v13.v12.v11
    for attr in ['v10','v9','v8','v7','v6','v5']:
        module.extension_contract();module=getattr(module,attr)
    module.extension_contract();module.v4.plant_contract();module.v4.v3.counter_contract();module.v4.v3.v2.extension_contract()
    if not isinstance(battles,list) or not 1<=len(battles)<=1000:raise ValueError('Require 1–1000 battles')
    node=shutil.which('node')
    if not node:raise SimulatorError('Node runtime is not on PATH')
    run=subprocess.run([node,'--experimental-default-type=module',str(BRIDGE)],
        input=json.dumps(battles,ensure_ascii=False,allow_nan=False),text=True,encoding='utf-8',cwd=ROOT,capture_output=True,timeout=timeout)
    if run.returncode:raise SimulatorError(run.stderr.strip())
    results=json.loads(run.stdout)
    if len(results)!=len(battles):raise SimulatorError('Batch result count mismatch')
    return {'results':results,'engine':engine_contract(),'adapter_contract':{'schema':'complete-single-battle-diagnostic-v17',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),
        'current_server_verified':False,'training_label_allowed':False}
