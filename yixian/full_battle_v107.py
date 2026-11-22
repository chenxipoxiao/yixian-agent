"""Original1001 input binding after validation of the frozen v105 receipt."""
from copy import deepcopy
from pathlib import Path
import hashlib,json
from . import full_battle_v106 as previous
from . import full_battle_v105 as legacy_engine
from .combat_start_context_bindings_v7 import FIELD,validate_receipt
from .combat_start_context_bindings_v6 import validate_receipt as validate_legacy,project_legacy_inputs
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-heaven-spirit-binding-v107.json'
PROOF_SHA='028d9d8c5f4ca4c8bfb2f3afd53b13e56651bd56c1eca49bbde0d0daadfb6e2e'
UnresolvedBattle=previous.UnresolvedBattle
catalogue=previous.catalogue
derive_start_initiative=previous.derive_start_initiative

def extension_contract():
 raw=PROOF.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:raise UnresolvedBattle('heaven_preparation_v107:evidence_changed')
 facts=json.loads(raw)
 for path,h in facts['source_sha256'].items():
  if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=h:raise UnresolvedBattle('heaven_preparation_v107:source_changed:'+path)
 return facts

def compile_start(row,**kwargs):
 facts=extension_contract()
 expected=facts['admitted_records'].get(row.get('id'))
 if expected is None:
  if isinstance(kwargs.get('combat_context'),dict) and FIELD in kwargs['combat_context']:
   raise UnresolvedBattle('heaven_preparation_v107:unregistered_receipt')
  return previous.compile_start(row,**kwargs)
 return compile_bound_start(row,expected,**kwargs)

def compile_bound_start(row,expected,**kwargs):
 # v106 only extends exact random-stream bindings. Never bypass an applicable binding.
 if row['id'] in previous.extension_contract()['admitted_records']:
  raise UnresolvedBattle('heaven_preparation_v107:parameter_binding_conflict')
 old_expected=legacy_engine.extension_contract()['admitted_records'].get(row['id'])
 if old_expected is None:raise UnresolvedBattle('heaven_preparation_v107:legacy_receipt_not_admitted')
 try:
  context,switches=validate_receipt(row,kwargs.get('combat_context'),expected,old_expected)
  values=validate_legacy(row,context,old_expected)
  projected,translated,ashes,disabled=project_legacy_inputs(row,context,values)
  for index,switch in enumerate(switches):
   if switch is None:continue
   cp=translated['players'][index]
   if 'heaven_spirit_switch' in cp and cp['heaven_spirit_switch']!=switch:
    raise ValueError('heaven_preparation_v107:legacy_switch_conflict')
   cp['heaven_spirit_switch']=deepcopy(switch)
 except (ValueError,KeyError,TypeError) as error:raise UnresolvedBattle(str(error)) from error
 # This is the v105 translation boundary; the original source receipt is not rewritten.
 result=legacy_engine.previous.compile_start(projected,**{**kwargs,'combat_context':translated})
 if any(ashes):
  engraving=result['battle'].setdefault('season_engraving',{'players':[[],[]]})
  for index,entries in enumerate(ashes):
   engraving['players'][index].extend(entries)
   engraving['players'][index].sort(key=lambda value:value['strategy_id'])
 for index,player in enumerate(row['players']):
  result['effect_players'][index]['season_choices']=deepcopy(player['candidate_start']['xian_mo_strategies'])
 result['original_preparation_context_v105']={
  'evidence_sha256':legacy_engine.PROOF_SHA,'receipt_sha256':old_expected['receipt_sha256'],
  'snapshot_sha256':old_expected['snapshot_sha256'],'disabled1010_players':disabled,
  'scope':'original_recorded_battle_only','policy_observation_allowed':False,'counterfactual_reuse_allowed':False,'training_label_allowed':False}
 result['original_heaven_spirit_context_v107']={'evidence_sha256':PROOF_SHA,
  'receipt_sha256':expected['receipt_sha256'],'snapshot_sha256':expected['snapshot_sha256'],
  'legacy_receipt_sha256':expected['legacy_receipt_sha256'],'scope':'original_recorded_battle_only',
  'policy_observation_allowed':False,'counterfactual_reuse_allowed':False,'training_label_allowed':False}
 return result

def simulate_batch(battles,*,timeout=90):
 extension_contract()
 result=previous.simulate_batch(battles,timeout=timeout)
 result['adapter_contract']={**result['adapter_contract'],'schema':'complete-single-battle-diagnostic-v107',
  'heaven_spirit_binding_sha256':PROOF_SHA,'training_label_allowed':False}
 return result
