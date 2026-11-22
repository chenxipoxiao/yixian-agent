"""Bound original-replay preparation inputs over the frozen v104 runtime."""
from copy import deepcopy
from pathlib import Path
import hashlib, json
from . import full_battle_v104 as previous
from .combat_start_context_bindings_v6 import FIELD, validate_receipt, project_legacy_inputs

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'data/inspection/current-preparation-binding-v105.json'
PROOF_SHA = '2596b8dc60aa10515267e30cf55dd3b3bab5bdd6f74e9978557daf85c3ce2ba8'
UnresolvedBattle = previous.UnresolvedBattle
catalogue = previous.catalogue
derive_start_initiative = previous.derive_start_initiative


def extension_contract():
    raw = PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROOF_SHA:
        raise UnresolvedBattle('preparation_v105:evidence_changed')
    facts = json.loads(raw)
    for path, expected in facts['source_sha256'].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise UnresolvedBattle('preparation_v105:source_changed:' + path)
    return facts


def compile_start(row, **kwargs):
    facts = extension_contract()
    expected = facts['admitted_records'].get(row.get('id'))
    if expected is None:
        if isinstance(kwargs.get('combat_context'), dict) and FIELD in kwargs['combat_context']:
            raise UnresolvedBattle('preparation_v105:unregistered_receipt')
        return previous.compile_start(row, **kwargs)
    return compile_bound_start(row, expected, **kwargs)


def compile_bound_start(row, expected, **kwargs):
    context = kwargs.get('combat_context')
    try:
        values = validate_receipt(row, context, expected)
        projected, translated, ashes, disabled = project_legacy_inputs(row, context, values)
    except (ValueError, KeyError, TypeError) as error:
        raise UnresolvedBattle(str(error)) from error
    result = previous.compile_start(projected, **{**kwargs, 'combat_context': translated})
    if any(ashes):
        engraving = result['battle'].setdefault('season_engraving', {'players': [[], []]})
        for index, entries in enumerate(ashes):
            engraving['players'][index].extend(entries)
            engraving['players'][index].sort(key=lambda value: value['strategy_id'])
    for index, player in enumerate(row['players']):
        result['effect_players'][index]['season_choices'] = deepcopy(player['candidate_start']['xian_mo_strategies'])
    result['original_preparation_context_v105'] = {
        'evidence_sha256': PROOF_SHA, 'receipt_sha256': expected['receipt_sha256'],
        'snapshot_sha256': expected['snapshot_sha256'], 'disabled1010_players': disabled,
        'scope': 'original_recorded_battle_only', 'policy_observation_allowed': False,
        'counterfactual_reuse_allowed': False, 'training_label_allowed': False}
    return result


def simulate_batch(battles, *, timeout=90):
    extension_contract()
    result = previous.simulate_batch(battles, timeout=timeout)
    result['adapter_contract'] = {**result['adapter_contract'],
        'schema': 'complete-single-battle-diagnostic-v105',
        'preparation_binding_sha256': PROOF_SHA, 'training_label_allowed': False}
    return result
