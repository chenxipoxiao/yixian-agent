"""Record-conditioned16024 opening only; no unaligned random streams."""
from copy import deepcopy
import hashlib,json,shutil,subprocess
from pathlib import Path
from . import full_battle_v44r2 as v44
from .simulator import engine_contract,SimulatorError
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-falling-paper-v45.json'
PROOF_SHA='17c530b297fff385ed1897742680bc0cb83ccef568ac208084669d7a6c31bad1'
BRIDGE=ROOT/'tools/full_battle_bridge_v45.mjs'
UnresolvedBattle=v44.UnresolvedBattle
catalogue=v44.catalogue
derive_start_initiative=v44.derive_start_initiative
def digest_json(value):
 return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def snapshot_binding(row,context):
 # Outcomes, postbattle counters and terminal fields deliberately excluded.
 players=[{k:v for k,v in p.items() if k not in ['after_talent_counters','start_private_field_names']} for p in context['players']]
 return digest_json({'id':row['id'],'game_id':row['game_id'],'rules':row['source_rules_version'],
  'round':row['round'],'players':row['players'],'context_players':players,
  'source_raw_sha256':context['source_raw_sha256'],'game_mode':context['game_mode'],'season_mec':context['season_mec']})
def extension_contract():
 raw=PROOF.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('Falling paper evidence changed')
 facts=json.loads(raw)
 for p,h in facts['source_sha256'].items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('Falling paper source changed:'+p)
 return facts
def compile_start(row,**kwargs):
 extension_contract()
 owned=[]
 for p in row['players']:
  choices=p['candidate_start'].get('xian_mo_strategies')
  if not isinstance(choices,list) or any(type(x) is not int for x in choices):raise UnresolvedBattle('Explicit season choices required')
  if len(choices)!=len(set(choices)):raise UnresolvedBattle('Duplicate season choices')
  owned.append(16024 in choices)
 if not any(owned):return v44.compile_start(row,**kwargs)
 context=kwargs.get('combat_context')
 if not isinstance(context,dict):raise UnresolvedBattle('falling_paper_context_required')
 binding=context.get('falling_paper_record')
 if not isinstance(binding,dict) or binding!={'snapshot_sha256':snapshot_binding(row,context),'scope':'unchanged_recorded_battle_only'}:
  raise UnresolvedBattle('falling_paper_snapshot_binding_mismatch')
 params=context.get('battle_params')
 if not isinstance(params,list) or len(params)!=sum(owned):raise UnresolvedBattle('falling_paper_other_parameter_consumers_unresolved')
 if any(type(x) is not int or x not in range(4) for x in params):raise UnresolvedBattle('falling_paper_invalid_branch')
 evidence=row.get('battle_params_evidence')
 if not isinstance(evidence,dict) or evidence.get('entries')!=len(params) or evidence.get('sha256')!=digest_json(params):
  raise UnresolvedBattle('falling_paper_source_parameter_mismatch')
 projected=deepcopy(row)
 for p in projected['players']:
  p['candidate_start']['xian_mo_strategies']=[x for x in p['candidate_start']['xian_mo_strategies'] if x!=16024]
 result=v44.compile_start(projected,**kwargs)
 battle=result['battle']
 battle['falling_paper']={'owners':owned,'stream':list(params),'battle_sha256':digest_json(battle)}
 for i,p in enumerate(row['players']):result['effect_players'][i]['season_choices']=deepcopy(p['candidate_start']['xian_mo_strategies'])
 result['falling_paper_context']={'evidence_sha256':PROOF_SHA,'record_conditioned':True,'snapshot_sha256':binding['snapshot_sha256'],
  'full_parameter_stream_sha256':digest_json(params),'other_rng_allowed':False,'policy_observation_allowed':False,
  'counterfactual_reuse_allowed':False,'exchange_reward_authoritative':False,'training_label_allowed':False}
 return result

def simulate_batch(battles,*,timeout=90):
    extension_contract();v44.extension_contract();v43=v44.v43;v43.extension_contract();v42=v43.v42;v42.extension_contract();v41=v42.v41;v41.extension_contract();v40=v41.v40;v40.extension_contract();v39=v40.v39;v39.extension_contract();v38=v39.v38;v38.extension_contract();v37=v38.v37;v37.extension_contract();v36=v37.v36;v36.extension_contract();v35=v36.v35;v35.extension_contract();v34=v35.v34;v34.extension_contract();v33=v34.v33;v33.extension_contract();v32=v33.v32
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
    return {'results':results,'engine':engine_contract(),'adapter_contract':{'schema':'complete-single-battle-diagnostic-v45',
        'evidence_sha256':PROOF_SHA,'native_scheduler_reused':True,'current_content_complete':False},
        'bridge_sha256':hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),'current_server_verified':False,'training_label_allowed':False}
