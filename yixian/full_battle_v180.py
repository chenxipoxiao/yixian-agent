"""Exact original-preparation admissions over frozen v130 and v179 runtime.

The client reader rules are unchanged. Admission extensions live only in a
private compiler view; older module globals and original evidence stay frozen.
"""
from copy import deepcopy
from pathlib import Path
from types import FunctionType
import hashlib, json
from . import full_battle_v130 as previous
from .combat_compiler_view_v81 import isolated_compiler, compiler_modules
from . import combat_start_context_bindings_v6 as legacy
from . import combat_start_context_bindings_v7 as heaven
from .combat_season_inputs_v124 import validate_inputs

ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'data/inspection/current-preparation-sources-v180.json'
PROOF_SHA='f99aa706b131fbfe738d3d04d85002582c914755cd79240e18268b371d43a875'
UnresolvedBattle=previous.UnresolvedBattle
catalogue=previous.catalogue
derive_start_initiative=previous.derive_start_initiative

def extension_contract():
    raw=PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:
        raise UnresolvedBattle('preparation_v180:evidence_changed')
    facts=json.loads(raw)
    for name,expected in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:
            raise UnresolvedBattle('preparation_v180:source_changed:'+name)
    return facts

def validate_registration(row,context,facts):
    rid=row.get('id');expected=facts['legacy_admissions'].get(rid)
    if expected is None:
        raise UnresolvedBattle('preparation_v180:unregistered_record')
    try:
        legacy.validate_receipt(row,context,expected)
        h=facts['heaven_admissions'].get(rid)
        if h is not None:
            heaven.validate_receipt(row,context,h,expected)
        elif heaven.FIELD in context:
            raise ValueError('preparation_v180:unexpected_heaven_receipt')
        validate_inputs(row,context,facts['batch_receipts'][rid])
    except (ValueError,KeyError,TypeError) as error:
        raise UnresolvedBattle(str(error)) from error

def _extended_contract():
    # Rebound to the isolated ancestor namespace, without capturing closures.
    facts=deepcopy(_V180_BASE_CONTRACT())
    target=facts[_V180_FIELD]
    if set(target).intersection(_V180_ADDITIONS):
        raise UnresolvedBattle('preparation_v180:historical_admission_collision')
    target.update(deepcopy(_V180_ADDITIONS))
    return facts

def _private_view(facts):
    view=isolated_compiler(previous);modules=compiler_modules(view)
    for name,field,additions in [
        ('yixian.full_battle_v105','admitted_records',facts['legacy_admissions']),
        ('yixian.full_battle_v107','admitted_records',facts['heaven_admissions']),
        ('yixian.full_battle_v124','input_receipts',facts['batch_receipts']),
    ]:
        module=modules[name]
        module._V180_BASE_CONTRACT=module.extension_contract
        module._V180_FIELD=field
        module._V180_ADDITIONS=deepcopy(additions)
        module.extension_contract=FunctionType(_extended_contract.__code__,vars(module),'extension_contract')
    return view

def compile_start(row,**kwargs):
    facts=extension_contract()
    if row.get('id') not in facts['legacy_admissions']:
        return previous.compile_start(row,**kwargs)
    validate_registration(row,kwargs.get('combat_context'),facts)
    result=_private_view(facts).compile_start(row,**kwargs)
    result['original_preparation_admission_v180']={
        'evidence_sha256':PROOF_SHA,'legacy_receipt_sha256':facts['legacy_admissions'][row['id']]['receipt_sha256'],
        'scope':'original_recorded_battle_only','reader_rules_changed':False,
        'policy_observation_allowed':False,'counterfactual_reuse_allowed':False,'training_label_allowed':False}
    return result
