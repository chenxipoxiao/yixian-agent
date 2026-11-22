"""Restore current fate204's positive-qi conversion without replaying acquisition."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from . import full_battle_v83 as previous

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT/'data/inspection/current-mortal-body-v84.json'
PROOF_SHA = 'bdde42ec121660ea581fb0fa02c88ae9edea7f208196a9a5e1ace760a6488da2'
UnresolvedBattle = previous.UnresolvedBattle
catalogue = previous.catalogue
derive_start_initiative = previous.derive_start_initiative


def extension_contract():
    raw = PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROOF_SHA:
        raise UnresolvedBattle('mortal_body_v84:evidence_changed')
    facts = json.loads(raw)
    for name, expected in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise UnresolvedBattle('mortal_body_v84:source_changed:'+name)
    return facts


def compile_start(row, **kwargs):
    extension_contract()
    entries = []
    for source in row.get('players', []):
        start = source['candidate_start']
        fates, choices = start.get('talents'), start.get('xian_mo_strategies')
        if not isinstance(fates, list) or any(type(x) is not int for x in fates):
            raise UnresolvedBattle('mortal_body_v84:explicit_talents_required')
        if not isinstance(choices, list) or any(type(x) is not int for x in choices):
            raise UnresolvedBattle('mortal_body_v84:explicit_season_choices_required')
        owned = 204 in fates
        if owned and (fates.count(204) != 1 or len(choices) != len(set(choices))):
            raise UnresolvedBattle('mortal_body_v84:duplicate_ownership')
        if owned and source['character_id'] != 4000005:
            raise UnresolvedBattle('mortal_body_v84:non_native_owner_unresolved')
        entries.append({'owned': owned, 'season17071_owned': 17071 in choices})
    # Preserve every ancestor gate, including mode, complete contexts and unknown
    # season effects. Merely knowing17071's veto does not implement that effect.
    result = previous.compile_start(row, **kwargs)
    if not any(e['owned'] for e in entries):
        return result
    if result['context'].get('resonance_selected') != 0:
        raise UnresolvedBattle('mortal_body_v84:explicit_current_no_resonance_required')
    for index, entry in enumerate(entries):
        if not entry['owned']:
            continue
        player = result['battle']['players'][index]
        if player['character'] != 'dx5' or player.get('stance') != 1:
            raise UnresolvedBattle('mortal_body_v84:base_fist_stance_required')
        if 'mortal_body_stacks' in player:
            raise UnresolvedBattle('mortal_body_v84:duplicate_native_field')
        # The native positive-qi handler calls physique and returns before
        # qi storage/gain callbacks. Native post_deck_setup retains fist stance.
        player['mortal_body_stacks'] = int(not entry['season17071_owned'])
        declared = result['declared_components'][index]
        declared['preparation_fates_not_reapplied'] = [
            x for x in declared['preparation_fates_not_reapplied'] if x != 204]
        declared['fate204_combat_conversion'] = {
            **deepcopy(entry), 'enabled': bool(player['mortal_body_stacks']),
            'acquisition_replayed': False, 'counter_reapplied': False,
            'input_hp_or_physique_preadded': False, 'evidence_sha256': PROOF_SHA}
    result['mortal_body_v84_context'] = {
        'evidence_sha256': PROOF_SHA, 'players': entries,
        'scope': 'ordinary ranked no resonance; all previous admission gates retained',
        'training_label_allowed': False}
    return result


def simulate_batch(battles, *, timeout=90):
    extension_contract()
    result = previous.simulate_batch(battles, timeout=timeout)
    result['adapter_contract'] = {**result['adapter_contract'],
        'schema': 'complete-single-battle-diagnostic-v84',
        'mortal_body_evidence_sha256': PROOF_SHA,
        'runtime_bridge_unchanged_from_v83': True, 'training_label_allowed': False}
    return result
