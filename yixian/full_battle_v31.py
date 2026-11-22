"""Current ordinary Echo Formation prefix; frozen v30 retained."""
import hashlib,json,shutil,subprocess
from pathlib import Path
from . import full_battle_v30 as v30
from .simulator import engine_contract,SimulatorError
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-echo-formation-v31.json'
PROOF_SHA='9a399c23570b4ac2b4ed25ac7b37e44e7cc854dd95e22e4c9af4b9a86515a775'
BRIDGE=ROOT/'tools/full_battle_bridge_v31.mjs'
UnresolvedBattle=v30.UnresolvedBattle
derive_start_initiative=v30.derive_start_initiative
def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Echo formation evidence changed')
    facts=json.loads(raw)
    for p,h in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('Echo formation source changed:'+p)
    return facts
def catalogue():
    extension_contract()
    return v30.catalogue()
def compile_start(row,**kwargs):
    extension_contract()
    return v30.compile_start(row,**kwargs)

def simulate_batch(battles,*,timeout=90):
    extension_contract();v30.extension_contract()
    v29=v30.v29
    v29.extension_contract()
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
    return {'results':results,'engine':engine_contract(),'adapter_contract':{'schema':'complete-single-battle-diagnostic-v31',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),'current_server_verified':False,'training_label_allowed':False}
