"""Ordered original-hand Five Elements Flag over frozen v61."""
from copy import deepcopy
import hashlib,json,shutil,subprocess
from pathlib import Path
from . import full_battle_v61 as v61
v60=v61.v60
v59=v60.v59
from .simulator import engine_contract,SimulatorError
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-element-flag-v62r2.json'
PROOF_SHA='885436bc30ab371450a076e7948ca88ededc035a8d1f08998a0dd1cf17033e40'
BRIDGE=ROOT/'tools/full_battle_bridge_v62r2.mjs'
UnresolvedBattle=v59.UnresolvedBattle
derive_start_initiative=v59.derive_start_initiative
def catalogue():
 facts=extension_contract();cards,mapping,talents,season=v61.catalogue()
 for c in facts['cards']:
  if c['raw_id'] in mapping or c['runtime_id'] in mapping.values():raise UnresolvedBattle('Element flag mapping collision')
  mapping[c['raw_id']]=c['runtime_id']
 return cards,mapping,talents,season

def extension_contract():
 raw=PROOF.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Element flag evidence changed')
 facts=json.loads(raw)
 for p,h in facts['source_sha256'].items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('Element flag source changed:'+p)
 return facts

def compile_start(row,**kwargs):
 facts=extension_contract();ctx=kwargs.get('combat_context');hands=[None,None]
 if 'tables' not in kwargs:kwargs['tables']=catalogue()
 for i,p in enumerate(row['players']):
  if not any(c in [7000111,7010111,7020111] for c in p['candidate_start']['board']):continue
  if not isinstance(ctx,dict) or ctx.get('source_raw_sha256')!=row['source']['raw_sha256'] or not isinstance(ctx.get('players'),list) or len(ctx['players'])!=2:
   raise UnresolvedBattle('element_flag_source_context_required')
  private=ctx['players'][i];h=private.get('element_flag_hand')
  if not isinstance(h,dict) or h.get('origin')!='publicData.lastRoundData.handCards' or h.get('environment_only') is not True or h.get('source_raw_sha256')!=row['source']['raw_sha256'] or h.get('record_id')!=row['id'] or h.get('round')!=row['round'] or h.get('board')!=p['candidate_start']['board']:
   raise UnresolvedBattle('element_flag_hand_source_binding_required:'+str(i))
  raw=h.get('raw_cards')
  if not isinstance(raw,list) or len(raw)>256 or len(raw)!=private.get('hand_count') or any(type(c) is not int or str(c) not in facts['hand_metadata'] for c in raw):
   raise UnresolvedBattle('element_flag_hand_invalid:'+str(i))
  hands[i]=deepcopy(raw)
 result=v61.compile_start(row,**kwargs)
 if any(h is not None for h in hands):
  # No replay outcomes, typed random streams, or later-round fields enter this payload.
  result['battle']['element_flag']={'hands':hands}
  result['element_flag_context']={'evidence_sha256':PROOF_SHA,'source':'publicData.lastRoundData.handCards','policy_observation':False,'training_label_allowed':False}
 return result

def simulate_batch(battles,*,timeout=90):
 extension_contract();v61.extension_contract();v60.extension_contract();v59.extension_contract();v58=v59.v58;v58.extension_contract();v57=v58.v57;v57.extension_contract();v56=v57.v56;v56.extension_contract();v55=v56.v55;v55.extension_contract();v54=v55.v54;v54.extension_contract();v53=v54.v53;v53.extension_contract();v52=v53.v52;v52.extension_contract();v51=v52.v51;v51.extension_contract();v50=v51.v50;v50.extension_contract();v49=v50.v49;v49.extension_contract();v48=v49.v48;v48.extension_contract();v46=v48.v46;v46.extension_contract();v45=v46.v45;v45.extension_contract();v44=v45.v44;v44.extension_contract();v43=v44.v43;v43.extension_contract();v42=v43.v42;v42.extension_contract();v41=v42.v41;v41.extension_contract();v40=v41.v40;v40.extension_contract();v39=v40.v39;v39.extension_contract();v38=v39.v38;v38.extension_contract();v37=v38.v37;v37.extension_contract();v36=v37.v36;v36.extension_contract();v35=v36.v35;v35.extension_contract();v34=v35.v34;v34.extension_contract();v33=v34.v33;v33.extension_contract();v32=v33.v32
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
 run=subprocess.run([node,'--experimental-default-type=module',str(BRIDGE)],input=json.dumps(battles,ensure_ascii=False,allow_nan=False),text=True,encoding='utf8',cwd=ROOT,capture_output=True,timeout=timeout)
 if run.returncode:raise SimulatorError(run.stderr.strip())
 results=json.loads(run.stdout)
 if len(results)!=len(battles):raise SimulatorError('Batch result count mismatch')
 return {'results':results,'engine':engine_contract(),'adapter_contract':{'schema':'complete-single-battle-diagnostic-v62r2',
  'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'current_content_complete':False},
  'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),'current_server_verified':False,'training_label_allowed':False}
