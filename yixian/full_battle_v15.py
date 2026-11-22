"""Current HP-for-qi payment and verified base stance/fate projection."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from . import full_battle_v14 as v14
from .simulator import engine_contract, SimulatorError

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-qi-stance-v15.json'
PROOF_SHA='d72e91658c262526e4dc42204eb16d9e4f9b6911ae4a1c96c578d012f75400af'
BRIDGE=ROOT/'tools/full_battle_bridge_v15.mjs'
UnresolvedBattle=v14.UnresolvedBattle
catalogue=v14.catalogue
derive_start_initiative=v14.derive_start_initiative


def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Qi/stance evidence changed')
    facts=json.loads(raw)
    for path,digest in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:
            raise UnresolvedBattle('Qi/stance source changed:'+path)
    return facts


def compile_start(row,**kwargs):
    extension_contract();projected=deepcopy(row);extra=[]
    for p in projected['players']:
        s=p['candidate_start'];fates=s.get('talents');native={}
        if not isinstance(fates,list) or any(type(v) is not int for v in fates) or len(set(fates))!=len(fates):
            raise UnresolvedBattle('Unique explicit talents required')
        if {206,209}&set(fates) and p['character_id']!=4000005:
            raise UnresolvedBattle('Non-native stance fate context pending')
        if p['character_id']==4000005:native['stance']=1
        for fate,field in [(153,'unbounded_qi_stacks'),(206,'indomitable_will_stacks'),(209,'surge_of_qi_stacks')]:
            if fate in fates:native[field]=1
        s['talents']=[f for f in fates if f not in (153,206,209)]
        extra.append(native)
    result=v14.compile_start(projected,**kwargs)
    for p,raw,effect,native in zip(row['players'],result['battle']['players'],result['effect_players'],extra):
        for key,val in native.items():
            if key in raw:raise UnresolvedBattle('Duplicate native state:'+key)
            raw[key]=val
        effect['fates']=deepcopy(p['candidate_start']['talents'])
    result['current_qi_stance']={'evidence_sha256':PROOF_SHA,'players':extra,'training_label_allowed':False}
    return result


def simulate_batch(battles,*,timeout=90):
    extension_contract();v14.extension_contract();v14.v13.extension_contract();v14.v13.v12.extension_contract()
    module=v14.v13.v12.v11
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
    return {'results':results,'engine':engine_contract(),'adapter_contract':{'schema':'complete-single-battle-diagnostic-v15',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),
        'current_server_verified':False,'training_label_allowed':False}
