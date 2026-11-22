"""Three owner-timed sounds over frozen v51r2; no reward training admission."""
from copy import deepcopy
import hashlib,json,shutil,subprocess
from pathlib import Path
from . import full_battle_v51r2 as v51
from .simulator import engine_contract,SimulatorError
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-sound-control-v52.json'
PROOF_SHA='3ac8d98433a3186bf86df7dcc7f9e7337ea7b418639093bfa1c6aec7d8549001'
BRIDGE=ROOT/'tools/full_battle_bridge_v52.mjs'
UnresolvedBattle=v51.UnresolvedBattle
catalogue=v51.catalogue
derive_start_initiative=v51.derive_start_initiative
def extension_contract():
 raw=PROOF.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Sound control evidence changed')
 facts=json.loads(raw)
 for p,h in facts['source_sha256'].items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('Sound control source changed:'+p)
 return facts

def compile_start(row,**kwargs):
 extension_contract();projected=deepcopy(row);entries=[];context=kwargs.get('combat_context')
 for i,p in enumerate(projected['players']):
  start=p['candidate_start'];choices=start.get('xian_mo_strategies')
  if not isinstance(choices,list) or any(type(x) is not int for x in choices):raise UnresolvedBattle('Explicit season choices required')
  owned=sorted(set(choices)&{1003,1005,1007})
  if not owned:entries.append([]);continue
  if len(choices)!=len(set(choices)):raise UnresolvedBattle('Duplicate season choices')
  if (not isinstance(context,dict) or context.get('source_raw_sha256')!=row['source']['raw_sha256']
      or not isinstance(context.get('players'),list) or len(context['players'])!=2):
   raise UnresolvedBattle('sound_control_source_context_required')
  private=context['players'][i]
  if not isinstance(private,dict):raise UnresolvedBattle('sound_control_player_context_required')
  data=private.get('sound_control_switch')
  if (not isinstance(data,dict) or data.get('origin')!='privateData.xianMoData:preparation_switch'
      or data.get('source_raw_sha256')!=row['source']['raw_sha256'] or data.get('environment_only') is not True
      or data.get('selected_strategy_ids')!=owned):
   raise UnresolvedBattle('sound_control_preparation_switch_required:'+str(i))
  temp=data.get('temp_data')
  if (not isinstance(temp,dict) or any(k not in {str(x) for x in owned} for k in temp)
      or any(type(v) is not int or not -(2**31)<=v<2**31 for v in temp.values())):
   raise UnresolvedBattle('sound_control_switch_map_required:'+str(i))
  entries.append([{'strategy_id':id,'enabled':temp.get(str(id),0)==0} for id in owned])
  start['xian_mo_strategies']=[x for x in choices if x not in owned]
 result=v51.compile_start(projected,**kwargs)
 if any(entries):
  result['battle']['sound_control']={'players':entries,'raw_boards':[deepcopy(p['candidate_start']['board']) for p in row['players']]}
  for i,p in enumerate(row['players']):result['effect_players'][i]['season_choices']=deepcopy(p['candidate_start']['xian_mo_strategies'])
  result['sound_control_context']={'evidence_sha256':PROOF_SHA,'origin':'explicit start ownership and preparation switch',
   'scope':'environment_only_not_policy_observation','acquisition_rewards_reapplied':False,'training_label_allowed':False}
 return result

def simulate_batch(battles,*,timeout=90):
    extension_contract();v51.extension_contract();v50=v51.v50;v50.extension_contract();v49=v50.v49;v49.extension_contract();v48=v49.v48;v48.extension_contract();v46=v48.v46;v46.extension_contract();v45=v46.v45;v45.extension_contract();v44=v45.v44;v44.extension_contract();v43=v44.v43;v43.extension_contract();v42=v43.v42;v42.extension_contract();v41=v42.v41;v41.extension_contract();v40=v41.v40;v40.extension_contract();v39=v40.v39;v39.extension_contract();v38=v39.v38;v38.extension_contract();v37=v38.v37;v37.extension_contract();v36=v37.v36;v36.extension_contract();v35=v36.v35;v35.extension_contract();v34=v35.v34;v34.extension_contract();v33=v34.v33;v33.extension_contract();v32=v33.v32
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
    return {'results':results,'engine':engine_contract(),'adapter_contract':{'schema':'complete-single-battle-diagnostic-v52',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),'current_server_verified':False,'training_label_allowed':False}
