"""Original engraving source binding and first-use spirit serpent execution."""
from copy import deepcopy
from pathlib import Path
import hashlib,json
from . import full_battle_v112 as previous
from . import full_battle_v105 as legacy_engine
from . import full_battle_v80 as core
from .combat_compiler_view_v81 import isolated_compiler,compiler_modules
from .combat_start_context_bindings_v8 import FIELD,validate_receipt
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-engraving-serpent-v113.json'
PROOF_SHA='31fbe33cfc30180c5b1ca4d3b8c9ca155cbe88463bf812aeb6c2e62b17ac6da7'
BRIDGE=ROOT/'tools/full_battle_bridge_v113.mjs'
UnresolvedBattle=previous.UnresolvedBattle
catalogue=previous.catalogue
derive_start_initiative=previous.derive_start_initiative

def extension_contract():
 raw=PROOF.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('engraving_v113:evidence_changed')
 facts=json.loads(raw)
 for name,h in facts['source_sha256'].items():
  if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('engraving_v113:source_changed:'+name)
 return facts

def compile_start(row,**kwargs):
 facts=extension_contract();expected=facts['admitted_records'].get(row.get('id'))
 if expected is None:
  if isinstance(kwargs.get('combat_context'),dict) and FIELD in kwargs['combat_context']:
   raise UnresolvedBattle('engraving_v113:unregistered_receipt')
  return previous.compile_start(row,**kwargs)
 return compile_bound_start(row,expected,**kwargs)

def compile_bound_start(row,expected,**kwargs):
 old_expected=legacy_engine.extension_contract()['admitted_records'].get(row['id'])
 if old_expected is None:raise UnresolvedBattle('engraving_v113:legacy_receipt_required')
 try:context,entries=validate_receipt(row,kwargs.get('combat_context'),expected,old_expected)
 except (ValueError,KeyError,TypeError) as error:raise UnresolvedBattle(str(error)) from error
 #13002 input provenance is recovered, but its parameter consumer stays closed.
 if not any(e and 13017 in e['selected_strategy_ids'] for e in entries):
  return previous.compile_start(row,**{**kwargs,'combat_context':context})
 slots=[]
 for e in entries:
  if e and 13017 in e['selected_strategy_ids']:
   if '13017' not in e['temp_data']:raise UnresolvedBattle('engraving_v113:explicit_grid_required')
   slots.append([{'strategy_id':13017,'slot':e['temp_data']['13017']}])
  else:slots.append([])
 view=isolated_compiler(previous);modules=compiler_modules(view)
 for name in ['yixian.full_battle_v105','yixian.full_battle_v107']:
  module=modules.get(name)
  if module is None:continue
  original=module.project_legacy_inputs
  def project(original_row,original_context,values,_original=original):
   projected,translated,ashes,disabled=_original(original_row,original_context,values)
   for player in projected['players']:
    owned=player['candidate_start']['xian_mo_strategies']
    player['candidate_start']['xian_mo_strategies']=[x for x in owned if x!=13017]
   return projected,translated,ashes,disabled
  module.project_legacy_inputs=project
 result=view.compile_start(row,**{**kwargs,'combat_context':context})
 engraving=result['battle'].setdefault('season_engraving',{'players':[[],[]]})
 for i,values in enumerate(slots):
  engraving['players'][i].extend(values);engraving['players'][i].sort(key=lambda x:x['strategy_id'])
  result['effect_players'][i]['season_choices']=deepcopy(row['players'][i]['candidate_start']['xian_mo_strategies'])
 result['original_engraving_context_v113']={'evidence_sha256':PROOF_SHA,**expected,
  'scope':'original_recorded_battle_only','policy_observation_allowed':False,'counterfactual_reuse_allowed':False,'training_label_allowed':False}
 return result

def simulate_batch(battles,*,timeout=90):
 extension_contract()
 for module in compiler_modules(previous).values():
  contract=vars(module).get('extension_contract')
  if contract is not None:contract()
 result=isolated_compiler(core,runtime_bridge=BRIDGE).simulate_batch(battles,timeout=timeout)
 result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v113',
  'engraving_evidence_sha256':PROOF_SHA,'training_label_allowed':False}
 return result
