"""Explicit7069 original hand/board classification, retaining frozen v34."""
from copy import deepcopy
import hashlib,json,shutil,subprocess
from pathlib import Path
from . import full_battle_v34 as v34
from .simulator import engine_contract,SimulatorError
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-clouds-rain-v35.json'
PROOF_SHA='3696bb4f67942d1ccb6fcd31d2071d6169a7ed2633a327e34a81ac4201b66ae7'
BRIDGE=ROOT/'tools/full_battle_bridge_v35.mjs'
UnresolvedBattle=v34.UnresolvedBattle
catalogue=v34.catalogue
derive_start_initiative=v34.derive_start_initiative
def extension_contract():
 raw=PROOF.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Clouds Rain evidence changed')
 facts=json.loads(raw)
 for p,h in facts['source_sha256'].items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('Clouds Rain source changed:'+p)
 return facts
def compile_start(row,**kwargs):
 facts=extension_contract();projected=deepcopy(row);entries=[];ctx=kwargs.get('combat_context')
 for i,p in enumerate(projected['players']):
  s=p['candidate_start'];choices=s.get('xian_mo_strategies')
  if not isinstance(choices,list) or any(type(v) is not int for v in choices):raise UnresolvedBattle('Explicit season choices required')
  if 7069 not in choices:entries.append(None);continue
  if len(choices)!=len(set(choices)):raise UnresolvedBattle('Duplicate season choices')
  if p['character_id']!=1000003 or any(x in s['talents'] for x in [20096,192]) or s['used_keyin_cards'] or any(13000<=x<14000 for x in choices):
   raise UnresolvedBattle('clouds_rain_conditional_classification_pending')
  if not isinstance(ctx,dict) or ctx.get('source_raw_sha256')!=row['source']['raw_sha256'] or not isinstance(ctx.get('players'),list) or len(ctx['players'])!=2:
   raise UnresolvedBattle('clouds_rain_source_context_required')
  private=ctx['players'][i];data=private.get('clouds_rain_hand')
  if not isinstance(data,dict) or data.get('origin')!='publicData.lastRoundData.handCards' or data.get('source_raw_sha256')!=row['source']['raw_sha256'] or data.get('environment_only') is not True:
   raise UnresolvedBattle('clouds_rain_hand_required:'+str(i))
  hand=data.get('raw_cards')
  if not isinstance(hand,list) or len(hand)>256 or any(type(c) is not int or str(c) not in facts['metadata'] for c in hand):
   raise UnresolvedBattle('clouds_rain_hand_invalid:'+str(i))
  if len(hand)!=private.get('hand_count'):raise UnresolvedBattle('clouds_rain_hand_count_mismatch:'+str(i))
  entries.append({'hand':deepcopy(hand),'board':deepcopy(s['board'])})
  s['xian_mo_strategies']=[v for v in choices if v!=7069]
 result=v34.compile_start(projected,**kwargs)
 if any(e is not None for e in entries):
  result['battle']['clouds_rain']={'players':entries}
  for i,p in enumerate(row['players']):result['effect_players'][i]['season_choices']=deepcopy(p['candidate_start']['xian_mo_strategies'])
  result['clouds_rain_context']={'evidence_sha256':PROOF_SHA,'source':'publicData.lastRoundData.handCards + usedCards',
   'policy_observation':False,'conditional_classification_supported':False,'training_label_allowed':False}
 return result
def simulate_batch(battles,*,timeout=90):
 extension_contract();v34.extension_contract();v33=v34.v33;v33.extension_contract();v32=v33.v32
 v32.extension_contract();v31=v32.v31;v31.extension_contract();v30=v31.v30;v30.extension_contract()
 v29=v30.v29;v29.extension_contract();v28=v29.v28;v28.extension_contract();v27=v28.v27;v26=v27.v26
 v27.extension_contract();v26.extension_contract();v26.v25.extension_contract();v26.v24.extension_contract()
 v26.v23.extension_contract();v26.v22.extension_contract();v26.v17.extension_contract();module=v26.v17.v16
 for attr in ['v15','v14','v13','v12','v11','v10','v9','v8','v7','v6','v5']:
  module.extension_contract();module=getattr(module,attr)
 module.extension_contract();module.v4.plant_contract();module.v4.v3.counter_contract();module.v4.v3.v2.extension_contract()
 if not isinstance(battles,list) or not 1<=len(battles)<=1000:raise ValueError('Require1–1000 battles')
 node=shutil.which('node')
 if not node:raise SimulatorError('Node runtime is not on PATH')
 run=subprocess.run([node,'--experimental-default-type=module',str(BRIDGE)],input=json.dumps(battles,ensure_ascii=False,allow_nan=False),text=True,encoding='utf8',cwd=ROOT,capture_output=True,timeout=timeout)
 if run.returncode:raise SimulatorError(run.stderr.strip())
 results=json.loads(run.stdout)
 if len(results)!=len(battles):raise SimulatorError('Batch result count mismatch')
 return {'results':results,'engine':engine_contract(),'adapter_contract':{'schema':'complete-single-battle-diagnostic-v35','evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'current_content_complete':False},
  'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),'current_server_verified':False,'training_label_allowed':False}
