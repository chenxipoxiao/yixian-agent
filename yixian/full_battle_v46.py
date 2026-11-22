"""Typed recorded parameters; diagnostic only and bound to original initiative."""
from copy import deepcopy
import hashlib,json,shutil,subprocess
from pathlib import Path
from . import full_battle_v45 as v45
from .simulator import engine_contract,SimulatorError
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-typed-parameters-v46.json'
PROOF_SHA='0930869a19a33277d9d0bed409e23388a016c0a6f5761d07bb7aaad91379f457'
BRIDGE=ROOT/'tools/full_battle_bridge_v46.mjs'
UnresolvedBattle=v45.UnresolvedBattle
catalogue=v45.catalogue
derive_start_initiative=v45.derive_start_initiative
digest_json=v45.digest_json
snapshot_binding=v45.snapshot_binding
def extension_contract():
 raw=PROOF.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Typed parameter evidence changed')
 facts=json.loads(raw)
 for p,h in facts['source_sha256'].items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('Typed parameter source changed:'+p)
 return facts
def compile_start(row,**kwargs):
 facts=extension_contract();context=kwargs.get('combat_context')
 if not isinstance(context,dict) or 'typed_parameter_record' not in context:return v45.compile_start(row,**kwargs)
 binding=context['typed_parameter_record'];owned=[]
 for p in row['players']:
  choices=p['candidate_start'].get('xian_mo_strategies')
  if not isinstance(choices,list) or any(type(x) is not int for x in choices) or len(choices)!=len(set(choices)):raise UnresolvedBattle('typed_parameters_invalid_season_choices')
  owned.append(16024 in choices)
 if not any(owned):raise UnresolvedBattle('typed_parameters_opening_owner_required')
 if not isinstance(binding,dict) or set(binding)!={'snapshot_sha256','scope','first_player'} or binding.get('snapshot_sha256')!=snapshot_binding(row,context) or binding.get('scope')!='unchanged_recorded_battle_only' or type(binding.get('first_player')) is not int or binding['first_player'] not in (0,1):
  raise UnresolvedBattle('typed_parameters_snapshot_binding_mismatch')
 params=context.get('battle_params')
 if not isinstance(params,list) or not sum(owned)<len(params)<=256 or any(type(x) is not int or not 0<=x<=2147483647 for x in params):raise UnresolvedBattle('typed_parameters_invalid_complete_stream')
 evidence=row.get('battle_params_evidence')
 if not isinstance(evidence,dict) or evidence.get('entries')!=len(params) or evidence.get('sha256')!=digest_json(params):raise UnresolvedBattle('typed_parameters_source_parameter_mismatch')
 if not any(cid in {c['id'] for c in facts['cards']} for p in row['players'] for cid in p['candidate_start']['board']):raise UnresolvedBattle('typed_parameters_supported_card_required')
 projected=deepcopy(row)
 for p in projected['players']:p['candidate_start']['xian_mo_strategies']=[x for x in p['candidate_start']['xian_mo_strategies'] if x!=16024]
 result=v45.v44.compile_start(projected,**kwargs);battle=result['battle']
 if battle['first_player']!=binding['first_player']:raise UnresolvedBattle('typed_parameters_initiative_binding_mismatch')
 battle['typed_parameters']={'owners':owned,'stream':list(params),'battle_sha256':digest_json(battle)}
 for i,p in enumerate(row['players']):result['effect_players'][i]['season_choices']=deepcopy(p['candidate_start']['xian_mo_strategies'])
 result['typed_parameter_context']={'evidence_sha256':PROOF_SHA,'snapshot_sha256':binding['snapshot_sha256'],'first_player':binding['first_player'],'full_parameter_stream_sha256':digest_json(params),'record_conditioned':True,'policy_observation_allowed':False,'counterfactual_reuse_allowed':False,'training_label_allowed':False}
 return result

def simulate_batch(battles,*,timeout=90):
    extension_contract();v45.extension_contract();v44=v45.v44;v44.extension_contract();v43=v44.v43;v43.extension_contract();v42=v43.v42;v42.extension_contract();v41=v42.v41;v41.extension_contract();v40=v41.v40;v40.extension_contract();v39=v40.v39;v39.extension_contract();v38=v39.v38;v38.extension_contract();v37=v38.v37;v37.extension_contract();v36=v37.v36;v36.extension_contract();v35=v36.v35;v35.extension_contract();v34=v35.v34;v34.extension_contract();v33=v34.v33;v33.extension_contract();v32=v33.v32
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
    return {'results':results,'engine':engine_contract(),'adapter_contract':{'schema':'complete-single-battle-diagnostic-v46',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),'current_server_verified':False,'training_label_allowed':False}
