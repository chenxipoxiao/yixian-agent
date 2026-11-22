"""Explicit1001 preparation switch and owner ordered opening over frozen v33."""
from copy import deepcopy
import hashlib,json,shutil,subprocess
from pathlib import Path
from . import full_battle_v33 as v33
from .simulator import engine_contract,SimulatorError
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-heaven-spirit-v34.json'
PROOF_SHA='fe5f6d67feef8465c39109bc001a6bb3f1afc4646d729194df8eb061ccd8d884'
BRIDGE=ROOT/'tools/full_battle_bridge_v34.mjs'
UnresolvedBattle=v33.UnresolvedBattle
catalogue=v33.catalogue
derive_start_initiative=v33.derive_start_initiative

def extension_contract():
 raw=PROOF.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Heaven Spirit evidence changed')
 facts=json.loads(raw)
 for p,h in facts['source_sha256'].items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('Heaven Spirit source changed:'+p)
 return facts

def compile_start(row,**kwargs):
 extension_contract();projected=deepcopy(row);entries=[]
 context=kwargs.get('combat_context')
 for i,p in enumerate(projected['players']):
  start=p['candidate_start'];choices=start.get('xian_mo_strategies')
  if not isinstance(choices,list) or any(type(x) is not int for x in choices):
   raise UnresolvedBattle('Explicit xian_mo_strategies array required')
  if 1001 not in choices:entries.append(None);continue
  if len(choices)!=len(set(choices)):raise UnresolvedBattle('Duplicate season choices')
  if (not isinstance(context,dict) or context.get('source_raw_sha256')!=row['source']['raw_sha256']
      or not isinstance(context.get('players'),list) or len(context['players'])!=2):
   raise UnresolvedBattle('heaven_spirit_source_context_required')
  data=context['players'][i].get('heaven_spirit_switch')
  if (not isinstance(data,dict) or data.get('origin')!='privateData.xianMoData:preparation_switch'
      or data.get('source_raw_sha256')!=row['source']['raw_sha256'] or data.get('environment_only') is not True
      or data.get('selected_strategy_ids')!=[1001]):
   raise UnresolvedBattle('heaven_spirit_preparation_switch_required:'+str(i))
  temp=data.get('temp_data')
  if (not isinstance(temp,dict) or any(k!='1001' for k in temp)
      or any(type(v) is not int or not -(2**31)<=v<2**31 for v in temp.values())):
   raise UnresolvedBattle('heaven_spirit_switch_map_required:'+str(i))
  entries.append({'strategy_id':1001,'enabled':temp.get('1001',0)==0})
  start['xian_mo_strategies']=[x for x in choices if x!=1001]
 result=v33.compile_start(projected,**kwargs)
 if any(e is not None for e in entries):
  result['battle']['heaven_spirit']={'players':entries}
  for i,p in enumerate(row['players']):
   result['effect_players'][i]['season_choices']=deepcopy(p['candidate_start']['xian_mo_strategies'])
  result['heaven_spirit_context']={'evidence_sha256':PROOF_SHA,
    'origin':'privateData.xianMoData:preparation_switch','scope':'environment_only_not_policy_observation',
    'opening_phase':'owner normal fates then1001 then3001/plants/card openings',
    'acquisition_rewards_reapplied':False,'training_label_allowed':False}
 return result

def simulate_batch(battles,*,timeout=90):
    extension_contract();v33.extension_contract();v32=v33.v32
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
    return {'results':results,'engine':engine_contract(),'adapter_contract':{'schema':'complete-single-battle-diagnostic-v34',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),'current_server_verified':False,'training_label_allowed':False}
