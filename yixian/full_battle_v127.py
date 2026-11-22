"""Both Dream Divine Brush forms and realm4/5 Bearing the Load, over v126r2."""
from copy import deepcopy
from pathlib import Path
import hashlib,json
from . import full_battle_v126r2 as previous
from . import full_battle_v80 as core
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
from .full_battle_v45 import digest_json,snapshot_binding
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-dream-brush-load-v127.json'
PROOF_SHA='2c67f9860d4c3eab9874ac76798579dfb31acba4378abc2542093a568ca2f925'
BINDINGS=ROOT/'data/inspection/current-dream-parameters-v127.json'
BINDINGS_SHA='6504d903692f8d1b840a19a4ded940bad85db42fa640d1bcd4ac46f1ccbb9fd7'
BRIDGE=ROOT/'tools/full_battle_bridge_v127.mjs'
UnresolvedBattle=previous.UnresolvedBattle
derive_start_initiative=previous.derive_start_initiative
def read_contract(path,digest):
 raw=path.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=digest:raise UnresolvedBattle('dream_v127:evidence_changed')
 facts=json.loads(raw)
 for n,h in facts['source_sha256'].items():
  if hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('dream_v127:source_changed:'+n)
 return facts
def extension_contract():return read_contract(PROOF,PROOF_SHA)
def catalogue():
 cards,mapping,talents,season=previous.catalogue()
 for c in extension_contract()['cards']:
  if c['raw_id'] in mapping or c['runtime_id'] in mapping.values():raise UnresolvedBattle('dream_v127:mapping_collision')
  mapping[c['raw_id']]=c['runtime_id']
 return cards,mapping,talents,season
def compile_start(row,**kwargs):
 extension_contract()
 if 'tables' not in kwargs:kwargs['tables']=catalogue()
 result=previous.compile_start(row,**kwargs)
 facts=read_contract(BINDINGS,BINDINGS_SHA);expected=facts['random_bindings'].get(row['id'])
 if expected is not None:
  ctx=kwargs.get('combat_context');binding=expected['binding']
  if snapshot_binding(row,ctx)!=binding['snapshot_sha256']:raise UnresolvedBattle('dream_v127:original_snapshot_mismatch')
  stream=ctx.get('battle_params');evidence=row.get('battle_params_evidence',{})
  if (not isinstance(stream,list) or any(type(x)is not int for x in stream)
      or digest_json(stream)!=binding['stream_sha256'] or evidence.get('entries')!=len(stream)
      or evidence.get('sha256')!=binding['stream_sha256']):raise UnresolvedBattle('dream_v127:original_stream_required')
  battle=result['battle']
  if (digest_json(battle)!=expected['compiled_battle_sha256'] or battle['first_player']!=binding['first_player']
      or any('parameter' in k or k=='falling_paper' for k in battle)):raise UnresolvedBattle('dream_v127:original_compiled_start_required')
  battle['replay_parameters']={'stream':list(stream),'battle_sha256':digest_json(battle),'record_binding':deepcopy(binding)}
  result['replay_parameter_context_v127']={'evidence_sha256':BINDINGS_SHA,'record_conditioned':True,
   'policy_observation_allowed':False,'counterfactual_reuse_allowed':False,'training_label_allowed':False}
 return result
def simulate_batch(battles,*,timeout=90):
 extension_contract();read_contract(BINDINGS,BINDINGS_SHA)
 for module in compiler_modules(previous).values():
  contract=vars(module).get('extension_contract')
  if contract is not None:contract()
 result=isolated_compiler(core,runtime_bridge=BRIDGE).simulate_batch(battles,timeout=timeout)
 result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v127',
  'dream_brush_load_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
 return result
