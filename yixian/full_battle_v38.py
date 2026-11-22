"""Civet combat effect and unresolved authoritative destiny-gain receipt over v37."""
from copy import deepcopy
import hashlib,json,shutil,subprocess
from pathlib import Path
from . import full_battle_v37 as v37
from .simulator import engine_contract,SimulatorError
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-civet-v38.json'
PROOF_SHA='75a8f175659da11363f8d1d01ecb77fe1057c9e499a7ff1b547ded8acb34bf83'
BRIDGE=ROOT/'tools/full_battle_bridge_v38.mjs'
UnresolvedBattle=v37.UnresolvedBattle
derive_start_initiative=v37.derive_start_initiative
def extension_contract():
 raw=PROOF.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Civet evidence changed')
 facts=json.loads(raw)
 for p,h in facts['source_sha256'].items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('Civet source changed:'+p)
 return facts
def catalogue():
 facts=extension_contract();cards,mapping,talents,season=v37.catalogue()
 for card,alias in zip(facts['cards'],facts['runtime_ids']):
  if card['id'] in mapping or alias in mapping.values():raise UnresolvedBattle('Civet alias collision')
  mapping[card['id']]=alias
 return cards,mapping,talents,season
def compile_start(row,**kwargs):
 facts=extension_contract()
 if 'tables' not in kwargs:kwargs['tables']=catalogue()
 result=v37.compile_start(row,**kwargs)
 # Include mirror context only when the compiled executable inputs contain
 # this family (including supported hand-triggered cards). No outcome reads.
 encoded=json.dumps(result['battle'])
 if any('"'+alias+'"' in encoded for alias in facts['runtime_ids']):
  mirrors=[p.get('is_mirror') for p in result['effect_players']]
  if any(type(v) is not bool for v in mirrors):raise UnresolvedBattle('civet_explicit_mirror_context_required')
  result['battle']['civet']={'is_mirror':mirrors}
  result['civet_context']={'evidence_sha256':PROOF_SHA,'authoritative_destiny_gain_resolved':False,'training_label_allowed':False}
 return result

def simulate_batch(battles,*,timeout=90):
    extension_contract();v37.extension_contract();v36=v37.v36;v36.extension_contract();v35=v36.v35;v35.extension_contract();v34=v35.v34;v34.extension_contract();v33=v34.v33;v33.extension_contract();v32=v33.v32
    v32.extension_contract();v31=v32.v31;v31.extension_contract()
    v30=v31.v30;v30.extension_contract();v29=v30.v29;v29.extension_contract()
    v28=v29.v28;v28.extension_contract();v27=v28.v27;v26=v27.v26;v27.extension_contract()
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
    return {'results':results,'engine':engine_contract(),'adapter_contract':{'schema':'complete-single-battle-diagnostic-v38',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),'current_server_verified':False,'training_label_allowed':False}
