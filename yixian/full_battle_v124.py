"""Batch season effects over the unchanged v123 diagnostic compiler.

Private, per-call leaf substitution preserves each ancestor's original-source
checks. Replay-derived inputs remain environment-only and non-counterfactual.
"""
from copy import deepcopy
from pathlib import Path
from types import FunctionType
import hashlib,json
from . import full_battle_v123 as previous
from . import full_battle_v80 as core
from . import full_battle_v105 as legacy
from .full_battle_base_v124 import compile_start as batch_leaf
from .combat_season_preparation_v124 import compile_start as batch_preparation
from .combat_season_projection_v124 import project_legacy_inputs
from .combat_season_inputs_v124 import SWITCH_IDS,GRID_IDS,validate_inputs
from .combat_start_context_bindings_v6 import validate_receipt as validate_legacy
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
from .full_battle_v45 import digest_json,snapshot_binding
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-season-batch-v124.json'
PROOF_SHA='39a820f9c13b64cd5a34c5e6f6be70b5a0f5cad0c4de730ffbc07340a8858d3b'
BRIDGE=ROOT/'tools/full_battle_bridge_v124.mjs'
UnresolvedBattle=previous.UnresolvedBattle
catalogue=previous.catalogue
derive_start_initiative=previous.derive_start_initiative

def extension_contract():
 raw=PROOF.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('season_batch_v124:evidence_changed')
 facts=json.loads(raw)
 for name,h in facts['source_sha256'].items():
  if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('season_batch_v124:source_changed:'+name)
 return facts

def original_switches(row,context,facts):
 values=[{},{}]
 receipt=facts['input_receipts'].get(row.get('id'))
 if receipt is not None:
  try:values=validate_inputs(row,context,receipt)
  except (ValueError,KeyError,TypeError) as e:raise UnresolvedBattle(str(e)) from e
 if any(1010 in p['candidate_start'].get('xian_mo_strategies',[]) for p in row['players']):
  expected=legacy.extension_contract()['admitted_records'].get(row['id'])
  if expected:
   try:old=validate_legacy(row,context,expected)
   except (ValueError,KeyError,TypeError) as e:raise UnresolvedBattle(str(e)) from e
   for i,x in enumerate(old):
    if 1010 in x:
     if 1010 in values[i] and x[1010]!=values[i][1010]:raise UnresolvedBattle('season_batch_v124:conflicting1010')
     values[i][1010]=x[1010]
  else:
   # First-cohort receipts use the frozen v77 projection contract.
   from .preparation_context_v77 import FIELD,PROJECTION_SHA,required_ids,validate_entry
   if context.get('engraving_source_projection_sha256')==PROJECTION_SHA:
    for i,p in enumerate(row['players']):
     if 1010 in p['candidate_start']['xian_mo_strategies']:
      try:v=validate_entry(row,i,context['players'][i].get(FIELD),required_ids(p,context['players'][i]))
      except ValueError as e:raise UnresolvedBattle(str(e)) from e
      if 1010 in v:values[i][1010]=v[1010]
 return values

def owned_new_ids(row,facts,values):
 result=[]
 for i,p in enumerate(row['players']):
  owned=p['candidate_start'].get('xian_mo_strategies')
  if not isinstance(owned,list) or any(type(x)is not int for x in owned) or len(owned)!=len(set(owned)):
   raise UnresolvedBattle('season_batch_v124:explicit_unique_ownership')
  ids=set(owned)&set(facts['implemented_ids'])
  #13002 already has its own frozen original-stream consumer. No second
  #reader or weakened randomness contract is introduced by this batch.
  ids.discard(13002)
  if 1010 in ids and values[i].get(1010)!=0:
   if 1010 not in values[i]:raise UnresolvedBattle('season_batch_v124:explicit_switch_required:1010')
   ids.remove(1010)
  result.append(sorted(ids))
 return result

def rebind(fn,module):
 result=FunctionType(fn.__code__,vars(module),fn.__name__,fn.__defaults__)
 result.__kwdefaults__=deepcopy(fn.__kwdefaults__);return result

def compile_start(row,**kwargs):
 facts=extension_contract();context=kwargs.get('combat_context')
 if not isinstance(context,dict):return previous.compile_start(row,**kwargs)
 values=original_switches(row,context,facts);ids=owned_new_ids(row,facts,values)
 if not any(ids):return previous.compile_start(row,**kwargs)
 return compile_owned_start(row,context,values,ids,facts,**kwargs)

def compile_owned_start(row,context,values,ids,facts,**kwargs):
 players=[];engravings=[[],[]]
 for i,p in enumerate(row['players']):
  source=p['candidate_start'];data={'ids':ids[i],'raw_cards':deepcopy(source['board'])};owned=set(ids[i])
  required=owned&SWITCH_IDS
  if not required<=set(values[i]):raise UnresolvedBattle('season_batch_v124:explicit_switch_required:'+','.join(map(str,sorted(required-set(values[i])))))
  if required:data['switches']={str(x):values[i][x]==0 for x in sorted(required)}
  for x in sorted(owned&GRID_IDS):
   if x not in values[i]:raise UnresolvedBattle('season_batch_v124:explicit_grid_required:'+str(x))
   slot=values[i][x]
   if type(slot)is not int or not 0<=slot<len(source['board']):raise UnresolvedBattle('season_batch_v124:invalid_grid')
   engravings[i].append({'strategy_id':x,'slot':slot})
  if 7024 in owned:
   if not isinstance(source.get('permanentBuffTempDatas'),dict):raise UnresolvedBattle('season_batch_v124:complete_permanent_map_required')
   data['permanent']=deepcopy(source['permanentBuffTempDatas'])
  if owned&{7085,23058}:
   from .full_battle_v13 import _params
   if 199 in source['talents']:data['vase']=_params(context['players'][i],'privateTalentDatas','199')
   else:data['vase']=[]  # Explicit absence of the owning fate, not a missing field.
   if len(data['vase']) not in (0,3):raise UnresolvedBattle('season_batch_v124:explicit_vase_slots')
  players.append(data)
 # This marker is not accepted from callers and is added only after checking
 #the immutable original receipts. It authorizes the narrow1010 projection.
 if '_season_batch_v124' in context:raise UnresolvedBattle('season_batch_v124:external_private_marker')
 translated=deepcopy(context)
 translated['_season_batch_v124']={'active1010_players':[i for i,p in enumerate(players) if 1010 in p['ids']]}
 view=isolated_compiler(previous);modules=compiler_modules(view);leaf=modules['yixian.full_battle']
 leaf._V124_IDS=set(facts['implemented_ids'])-{13002,3013}
 if any(7024 in x for x in ids):leaf.PERMANENT_FIELDS=set(leaf.PERMANENT_FIELDS)|{'10037'}
 leaf.compile_start=rebind(batch_leaf,leaf)
 # v123 makes another private leaf when7120 is present; retain this extension.
 modules['yixian.full_battle_v123'].compile_7120_leaf=batch_leaf
 for name in ('yixian.full_battle_v105','yixian.full_battle_v107'):
  modules[name].project_legacy_inputs=project_legacy_inputs
 modules['yixian.full_battle_v77'].compile_start=rebind(batch_preparation,modules['yixian.full_battle_v77'])
 from .combat_season_swordsmith_v124 import compile_start as swordsmith_start
 modules['yixian.full_battle_v9'].compile_start=rebind(swordsmith_start,modules['yixian.full_battle_v9'])
 from .combat_season_vase_v124 import vase_projection
 modules['yixian.full_battle_v80']._vase_projection=rebind(vase_projection,modules['yixian.full_battle_v80'])
 result=view.compile_start(row,**{**kwargs,'combat_context':translated})
 if result['context'].get('resonance_selected')!=0:raise UnresolvedBattle('season_batch_v124:no_resonance_required')
 battle=result['battle']
 if any('parameter' in key or key=='falling_paper' for key in battle):
  # A new-effect start needs its own whole-payload binding. Existing frozen
  #random labels are not silently migrated onto the new interface.
  raise UnresolvedBattle('season_batch_v124:new_effect_random_binding_required')
 battle['season_batch']={'players':players,'source_binding':{'snapshot_sha256':snapshot_binding(row,context),
  'record_id':row['id'],'environment_only':True,'counterfactual_reuse_allowed':False}}
 if any(engravings):
  engraving=battle.setdefault('season_engraving',{'players':[[],[]]})
  for i,entries in enumerate(engravings):engraving['players'][i].extend(entries);engraving['players'][i].sort(key=lambda x:x['strategy_id'])
 for i,p in enumerate(row['players']):result['effect_players'][i]['season_choices']=deepcopy(p['candidate_start']['xian_mo_strategies'])
 result['season_batch_context_v124']={'evidence_sha256':PROOF_SHA,'ids':ids,'original_start_preserved':True,
  'private_inputs_bound_before_projection':True,'training_label_allowed':False}
 return result

def simulate_batch(battles,*,timeout=90):
 extension_contract()
 for module in compiler_modules(previous).values():
  contract=vars(module).get('extension_contract')
  if contract is not None:contract()
 result=isolated_compiler(core,runtime_bridge=BRIDGE).simulate_batch(battles,timeout=timeout)
 result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v124',
  'season_batch_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
 return result
