"""Original-record 16024 opening and later typed readers on one complete FIFO."""
from copy import deepcopy
import hashlib,json
from pathlib import Path
from . import full_battle_v100 as previous
from . import full_battle_v80 as core
from .full_battle_v45 import digest_json,snapshot_binding
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-paper-mixed-parameters-v101.json'
PROOF_SHA='766a3d852857ae92a4c8512e5efe88ea2341b09d5d219c0fdcfa577add58436f'
BRIDGE=ROOT/'tools/full_battle_bridge_v101.mjs'
UnresolvedBattle=previous.UnresolvedBattle
catalogue=previous.catalogue
derive_start_initiative=previous.derive_start_initiative

def extension_contract():
 raw=PROOF.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('paper_mixed_parameters_v101:evidence_changed')
 facts=json.loads(raw)
 for p,h in facts['source_sha256'].items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('paper_mixed_parameters_v101:source_changed:'+p)
 return facts

def compile_start(row,**kwargs):
 facts=extension_contract()
 expected=facts['admitted_records'].get(row.get('id'))
 if expected is None:return previous.compile_start(row,**kwargs)
 return compile_bound_start(row,expected,**kwargs)

def compile_projected_start(row,**kwargs):
 """Consume only the known 16024 ownership, as frozen v80 does at its fallback.

 The caller verifies the complete original snapshot before this projection.
 Every other ancestor check, including original-hand requirements, stays active.
 """
 owners=[];projected=deepcopy(row)
 for p in projected['players']:
  choices=p['candidate_start'].get('xian_mo_strategies')
  if not isinstance(choices,list) or any(type(x) is not int for x in choices) or len(choices)!=len(set(choices)):
   raise UnresolvedBattle('paper_mixed_parameters_v101:explicit_unique_season_choices_required')
  owners.append(16024 in choices)
  p['candidate_start']['xian_mo_strategies']=[x for x in choices if x!=16024]
 if not any(owners):raise UnresolvedBattle('paper_mixed_parameters_v101:opening_owner_required')
 result=previous.compile_start(projected,**kwargs)
 for i,p in enumerate(row['players']):result['effect_players'][i]['season_choices']=deepcopy(p['candidate_start']['xian_mo_strategies'])
 return result,owners

def compile_bound_start(row,expected,**kwargs):
 ctx=kwargs.get('combat_context');binding=expected['binding']
 if not isinstance(ctx,dict) or snapshot_binding(row,ctx)!=binding['snapshot_sha256']:
  raise UnresolvedBattle('paper_mixed_parameters_v101:original_snapshot_mismatch')
 if ctx.get('falling_paper_record')!={'snapshot_sha256':binding['snapshot_sha256'],'scope':'unchanged_recorded_battle_only'}:
  raise UnresolvedBattle('paper_mixed_parameters_v101:opening_snapshot_binding_mismatch')
 params=ctx.get('battle_params')
 if not isinstance(params,list) or not 1<len(params)<=256 or any(type(x) is not int or not -1<=x<=2147483647 for x in params) or digest_json(params)!=binding['stream_sha256']:
  raise UnresolvedBattle('paper_mixed_parameters_v101:recorded_stream_mismatch')
 evidence=row.get('battle_params_evidence',{})
 if evidence.get('entries')!=len(params) or evidence.get('sha256')!=binding['stream_sha256']:
  raise UnresolvedBattle('paper_mixed_parameters_v101:source_parameter_mismatch')
 result,owners=compile_projected_start(row,**kwargs);battle=result['battle']
 if any('parameter' in k or k=='falling_paper' for k in battle):
  raise UnresolvedBattle('paper_mixed_parameters_v101:mixed_parameter_handlers')
 if owners!=expected['owners'] or digest_json(battle)!=expected['compiled_battle_sha256'] or battle['first_player']!=binding['first_player']:
  raise UnresolvedBattle('paper_mixed_parameters_v101:unaudited_compiled_start')
 battle['paper_mixed_parameters']={'owners':owners,'stream':list(params),'battle_sha256':digest_json(battle),'record_binding':deepcopy(binding)}
 result['paper_mixed_parameter_context_v101']={'evidence_sha256':PROOF_SHA,'record_conditioned':True,
  'snapshot_sha256':binding['snapshot_sha256'],'first_player':binding['first_player'],
  'full_parameter_stream_sha256':binding['stream_sha256'],'ownership_projection':[16024],
  'policy_observation_allowed':False,'counterfactual_reuse_allowed':False,
  'exchange_reward_authoritative':False,'training_label_allowed':False}
 return result

def simulate_batch(battles,*,timeout=90):
 extension_contract()
 for module in compiler_modules(previous).values():
  contract=vars(module).get('extension_contract')
  if contract is not None:contract()
 result=isolated_compiler(core,runtime_bridge=BRIDGE).simulate_batch(battles,timeout=timeout)
 result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v101',
  'paper_mixed_parameters_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
 return result
