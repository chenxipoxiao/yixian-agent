"""Owner-ordered three-season opening batch; frozen v50r2 is unchanged."""
from copy import deepcopy
import hashlib,json,shutil,subprocess
from pathlib import Path
from . import full_battle_v50r2 as v50
from .simulator import engine_contract,SimulatorError
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-season-opening-v51.json'
PROOF_SHA='771b2817894766f06062ea5589d50a2ae510d2e5afbce3b77372733734335b70'
BRIDGE=ROOT/'tools/full_battle_bridge_v51r2.mjs'
UnresolvedBattle=v50.UnresolvedBattle
catalogue=v50.catalogue
derive_start_initiative=v50.derive_start_initiative
def extension_contract():
 raw=PROOF.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Season opening evidence changed')
 facts=json.loads(raw)
 extra=ROOT/'data/inspection/engraving-dream-identities-v51r2.json'
 if hashlib.sha256(extra.read_bytes()).hexdigest()!='0596971ed6c1e7560a81ab89ba588e4f5f19a15648026c1291ead0b62036f95a':raise UnresolvedBattle('Dream identity evidence changed')
 for p,h in json.loads(extra.read_text('utf8'))['source_sha256'].items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('Dream identity source changed:'+p)
 for p,h in facts['source_sha256'].items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('Season opening source changed:'+p)
 return facts

def compile_start(row,**kwargs):
 extension_contract();projected=deepcopy(row);entries=[];context=kwargs.get('combat_context')
 for i,p in enumerate(projected['players']):
  start=p['candidate_start'];choices=start.get('xian_mo_strategies')
  if not isinstance(choices,list) or any(type(x) is not int for x in choices):raise UnresolvedBattle('Explicit season choices required')
  owned=[x for x in choices if x in (1002,3002,7105)]
  if not owned:entries.append([]);continue
  if len(choices)!=len(set(choices)):raise UnresolvedBattle('Duplicate season choices')
  seat=[]
  for id in owned:
   e={'strategy_id':id}
   if id==1002:
    if (not isinstance(context,dict) or context.get('source_raw_sha256')!=row['source']['raw_sha256']
        or not isinstance(context.get('players'),list) or len(context['players'])!=2):
     raise UnresolvedBattle('wild_dance_source_context_required')
    private=context['players'][i]
    if not isinstance(private,dict):raise UnresolvedBattle('wild_dance_player_context_required')
    data=private.get('wild_dance_switch')
    if (not isinstance(data,dict) or data.get('origin')!='privateData.xianMoData:preparation_switch'
        or data.get('source_raw_sha256')!=row['source']['raw_sha256'] or data.get('environment_only') is not True
        or data.get('selected_strategy_ids')!=[1002]):
     raise UnresolvedBattle('wild_dance_preparation_switch_required:'+str(i))
    temp=data.get('temp_data')
    if (not isinstance(temp,dict) or any(k!='1002' for k in temp)
        or any(type(v) is not int or not -(2**31)<=v<2**31 for v in temp.values())):
     raise UnresolvedBattle('wild_dance_switch_map_required:'+str(i))
    e['enabled']=temp.get('1002',0)==0
   seat.append(e)
  entries.append(seat);start['xian_mo_strategies']=[x for x in choices if x not in owned]
 result=v50.compile_start(projected,**kwargs)
 if any(entries):
  result['battle']['season_opening_batch']={'players':entries}
  for i,p in enumerate(row['players']):result['effect_players'][i]['season_choices']=deepcopy(p['candidate_start']['xian_mo_strategies'])
  result['season_opening_context']={'evidence_sha256':PROOF_SHA,'origin':'explicit start ownership and preparation switch',
   'scope':'environment_only_not_policy_observation','acquisition_rewards_reapplied':False,'training_label_allowed':False}
 return result

def simulate_batch(battles,*,timeout=90):
    extension_contract();v50.extension_contract();v49=v50.v49;v49.extension_contract();v48=v49.v48;v48.extension_contract();v46=v48.v46;v46.extension_contract();v45=v46.v45;v45.extension_contract();v44=v45.v44;v44.extension_contract();v43=v44.v43;v43.extension_contract();v42=v43.v42;v42.extension_contract();v41=v42.v41;v41.extension_contract();v40=v41.v40;v40.extension_contract();v39=v40.v39;v39.extension_contract();v38=v39.v38;v38.extension_contract();v37=v38.v37;v37.extension_contract();v36=v37.v36;v36.extension_contract();v35=v36.v35;v35.extension_contract();v34=v35.v34;v34.extension_contract();v33=v34.v33;v33.extension_contract();v32=v33.v32
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
    return {'results':results,'engine':engine_contract(),'adapter_contract':{'schema':'complete-single-battle-diagnostic-v51r2',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),'current_server_verified':False,'training_label_allowed':False}
