"""Current Yan Chen card corrections over all frozen v25 start rules."""
import hashlib,json,shutil,subprocess
from pathlib import Path
from . import full_battle_v25 as v25, full_battle_v24 as v24, full_battle_v23 as v23, full_battle_v22 as v22, full_battle_v17 as v17
from .simulator import engine_contract,SimulatorError
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-yan-chen-cards-v26.json'
PROOF_SHA='dfcafc34d258db4c99d087f1d206f57e57a0211a09eb47e1fa2f52edde066202'
BRIDGE=ROOT/'tools/full_battle_bridge_v26.mjs'
UnresolvedBattle=v25.UnresolvedBattle
catalogue=v25.catalogue

def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Yan Chen evidence changed')
    facts=json.loads(raw)
    for p,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('Yan Chen source changed:'+p)
    return facts

def compile_start(row,**kwargs):
    extension_contract()
    return v25.compile_start(row,**kwargs)

def derive_start_initiative(row,**kwargs):
    extension_contract()
    return v25.derive_start_initiative(row,**kwargs)

def simulate_batch(battles,*,timeout=90):
    extension_contract();v25.extension_contract();v24.extension_contract();v23.extension_contract();v22.extension_contract();v17.extension_contract()
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
    return {'results':results,'engine':engine_contract(),'adapter_contract':{'schema':'complete-single-battle-diagnostic-v26',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),'current_server_verified':False,'training_label_allowed':False}
