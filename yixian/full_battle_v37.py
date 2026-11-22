"""7056 before-card star-slot effects over frozen v36."""
from copy import deepcopy
import hashlib,json,shutil,subprocess
from pathlib import Path
from . import full_battle_v36 as v36
from .simulator import engine_contract,SimulatorError
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-seven-stars-v37.json'
PROOF_SHA='7bdfbb787dfb8144a1025287c0b1c9764a7fa708c972f5ec9ac18f52d1af0611'
BRIDGE=ROOT/'tools/full_battle_bridge_v37.mjs'
UnresolvedBattle=v36.UnresolvedBattle
catalogue=v36.catalogue
derive_start_initiative=v36.derive_start_initiative
def extension_contract():
 raw=PROOF.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Seven Stars evidence changed')
 facts=json.loads(raw)
 for p,h in facts['source_sha256'].items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('Seven Stars source changed:'+p)
 return facts
def compile_start(row,**kwargs):
 extension_contract();projected=deepcopy(row);entries=[]
 for p in projected['players']:
  s=p['candidate_start'];choices=s.get('xian_mo_strategies')
  if not isinstance(choices,list) or any(type(x) is not int for x in choices):raise UnresolvedBattle('Explicit season choices required')
  if 7056 not in choices:entries.append(None);continue
  if len(choices)!=len(set(choices)):raise UnresolvedBattle('Duplicate season choices')
  n=s.get('unlocked_slots')
  if type(n) is not int or not 3<=n<=8 or not isinstance(s.get('board'),list) or len(s['board'])!=n:
   raise UnresolvedBattle('seven_stars_explicit_unlocked_grids_required')
  entries.append({'strategy_id':7056,'unlocked_slots':n});s['xian_mo_strategies']=[x for x in choices if x!=7056]
 result=v36.compile_start(projected,**kwargs)
 if any(e is not None for e in entries):
  result['battle']['seven_stars']={'players':entries}
  for i,p in enumerate(row['players']):result['effect_players'][i]['season_choices']=deepcopy(p['candidate_start']['xian_mo_strategies'])
  result['seven_stars_context']={'evidence_sha256':PROOF_SHA,'charges':7,'phase':'before_card_body',
   'temporary_card_identity_supported':False,'acquisition_rewards_reapplied':False,'training_label_allowed':False}
 return result

def simulate_batch(battles,*,timeout=90):
    extension_contract();v36.extension_contract();v35=v36.v35;v35.extension_contract();v34=v35.v34;v34.extension_contract();v33=v34.v33;v33.extension_contract();v32=v33.v32
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
    return {'results':results,'engine':engine_contract(),'adapter_contract':{'schema':'complete-single-battle-diagnostic-v37',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),'current_server_verified':False,'training_label_allowed':False}
