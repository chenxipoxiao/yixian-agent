"""Original-record 16024 opening and later typed readers on one complete FIFO."""
from copy import deepcopy
import hashlib,json
from pathlib import Path
from . import full_battle_v101 as previous
from . import full_battle_v80 as core
from .full_battle_v45 import digest_json,snapshot_binding
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-flag-paper-parameters-v102.json'
PROOF_SHA='1486e926ce04d9d0ff241da40f664b17f803beaf53ea7629fd88acb49ed7d411'
BRIDGE=ROOT/'tools/full_battle_bridge_v102.mjs'
UnresolvedBattle=previous.UnresolvedBattle
catalogue=previous.catalogue
derive_start_initiative=previous.derive_start_initiative

def extension_contract():
 raw=PROOF.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('paper_mixed_parameters_v102:evidence_changed')
 facts=json.loads(raw)
 for p,h in facts['source_sha256'].items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('paper_mixed_parameters_v102:source_changed:'+p)
 return facts

def compile_start(row,**kwargs):
 facts=extension_contract()
 expected=facts['admitted_records'].get(row.get('id'))
 if expected is None:return previous.compile_start(row,**kwargs)
 return compile_bound_start(row,expected,**kwargs)

compile_projected_start=previous.compile_projected_start

def compile_bound_start(row,expected,**kwargs):
 ctx=kwargs.get('combat_context');binding=expected['binding']
 if not isinstance(ctx,dict) or snapshot_binding(row,ctx)!=binding['snapshot_sha256']:
  raise UnresolvedBattle('paper_mixed_parameters_v102:original_snapshot_mismatch')
 if ctx.get('falling_paper_record')!={'snapshot_sha256':binding['snapshot_sha256'],'scope':'unchanged_recorded_battle_only'}:
  raise UnresolvedBattle('paper_mixed_parameters_v102:opening_snapshot_binding_mismatch')
 params=ctx.get('battle_params')
 if not isinstance(params,list) or not 1<len(params)<=256 or any(type(x) is not int or not -1<=x<=2147483647 for x in params) or digest_json(params)!=binding['stream_sha256']:
  raise UnresolvedBattle('paper_mixed_parameters_v102:recorded_stream_mismatch')
 evidence=row.get('battle_params_evidence',{})
 if evidence.get('entries')!=len(params) or evidence.get('sha256')!=binding['stream_sha256']:
  raise UnresolvedBattle('paper_mixed_parameters_v102:source_parameter_mismatch')
 result,owners=compile_projected_start(row,**kwargs);battle=result['battle']
 if any('parameter' in k or k=='falling_paper' for k in battle):
  raise UnresolvedBattle('paper_mixed_parameters_v102:mixed_parameter_handlers')
 if owners!=expected['owners'] or digest_json(battle)!=expected['compiled_battle_sha256'] or battle['first_player']!=binding['first_player']:
  raise UnresolvedBattle('paper_mixed_parameters_v102:unaudited_compiled_start')
 battle['paper_mixed_parameters']={'owners':owners,'stream':list(params),'battle_sha256':digest_json(battle),'record_binding':deepcopy(binding)}
 result['flag_paper_parameter_context_v102']={'evidence_sha256':PROOF_SHA,'record_conditioned':True,
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
 result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v102',
  'paper_mixed_parameters_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
 return result
