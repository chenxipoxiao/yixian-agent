"""Original-start replay bindings using frozen, typed random consumers."""
from copy import deepcopy
import hashlib,json
from pathlib import Path
from . import full_battle_v97 as previous
from . import full_battle_v80 as core
from .full_battle_v45 import digest_json,snapshot_binding
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-mixed-parameters-v98.json'
PROOF_SHA='84dbf6299d303406079a963b21f16572d3906e1e134d22fe0a379816f0713073'
BRIDGE=ROOT/'tools/full_battle_bridge_v98.mjs'
UnresolvedBattle=previous.UnresolvedBattle
catalogue=previous.catalogue
derive_start_initiative=previous.derive_start_initiative

def extension_contract():
 raw=PROOF.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('mixed_parameters_v98:evidence_changed')
 facts=json.loads(raw)
 for p,h in facts['source_sha256'].items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('mixed_parameters_v98:source_changed:'+p)
 return facts

def compile_start(row,**kwargs):
 facts=extension_contract()
 expected=facts['admitted_records'].get(row.get('id'))
 if expected is None:return previous.compile_start(row,**kwargs)
 return compile_bound_start(row,expected,**kwargs)

def compile_bound_start(row,expected,**kwargs):
 ctx=kwargs.get('combat_context');binding=expected['binding']
 if not isinstance(ctx,dict) or snapshot_binding(row,ctx)!=binding['snapshot_sha256']:
  raise UnresolvedBattle('mixed_parameters_v98:original_snapshot_mismatch')
 params=ctx.get('battle_params')
 if not isinstance(params,list) or not params or any(type(x) is not int for x in params) or digest_json(params)!=binding['stream_sha256']:
  raise UnresolvedBattle('mixed_parameters_v98:recorded_stream_mismatch')
 evidence=row.get('battle_params_evidence',{})
 if evidence.get('entries')!=len(params) or evidence.get('sha256')!=binding['stream_sha256']:
  raise UnresolvedBattle('mixed_parameters_v98:source_parameter_mismatch')
 result=previous.compile_start(row,**kwargs);battle=result['battle']
 if any('parameter' in k or k=='falling_paper' for k in battle):
  raise UnresolvedBattle('mixed_parameters_v98:mixed_parameter_handlers')
 if digest_json(battle)!=expected['compiled_battle_sha256'] or battle['first_player']!=binding['first_player']:
  raise UnresolvedBattle('mixed_parameters_v98:unaudited_compiled_start')
 battle['mixed_parameters']={'stream':list(params),'battle_sha256':digest_json(battle),'record_binding':deepcopy(binding)}
 result['mixed_parameter_context_v98']={'evidence_sha256':PROOF_SHA,'mode':expected['mode'],'record_conditioned':True,
  'snapshot_sha256':binding['snapshot_sha256'],'first_player':binding['first_player'],
  'full_parameter_stream_sha256':binding['stream_sha256'],'policy_observation_allowed':False,
  'counterfactual_reuse_allowed':False,'training_label_allowed':False}
 return result

def simulate_batch(battles,*,timeout=90):
 extension_contract()
 for module in compiler_modules(previous).values():
  contract=vars(module).get('extension_contract')
  if contract is not None:contract()
 result=isolated_compiler(core,runtime_bridge=BRIDGE).simulate_batch(battles,timeout=timeout)
 result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v98',
  'mixed_parameters_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
 return result
