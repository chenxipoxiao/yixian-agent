"""Explicit fate198 opening over the unchanged v81 diagnostic adapter."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from . import full_battle_v81 as previous
from .combat_compiler_view_v81 import isolated_compiler

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'data/inspection/current-scroll-opening-v82.json'
PROOF_SHA = '4cc90c92b7bba5d2103178a7677cf30c9db6863500a68d1bede2b62b691ca177'
BRIDGE = ROOT / 'tools/full_battle_bridge_v82.mjs'
UnresolvedBattle = previous.UnresolvedBattle
catalogue = previous.catalogue
derive_start_initiative = previous.derive_start_initiative


def extension_contract():
    raw = PROOF.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROOF_SHA:
        raise UnresolvedBattle('scroll_opening_v82:evidence_changed')
    facts = json.loads(raw)
    for name, expected in facts['source_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise UnresolvedBattle('scroll_opening_v82:source_changed:' + name)
    return facts


def compile_start(row, **kwargs):
    facts = extension_contract()
    entries = []
    for player in row.get('players', []):
        start = player['candidate_start']
        choices = start.get('talents')
        if not isinstance(choices, list) or any(type(x) is not int for x in choices):
            raise UnresolvedBattle('scroll_opening_v82:explicit_talents_required')
        if 198 in choices and len(choices) != len(set(choices)):
            raise UnresolvedBattle('scroll_opening_v82:duplicate_talents')
        entries.append({'fate_ids': [198] if 198 in choices else [],
                        'starting_raw_cards': deepcopy(start.get('board')),
                        'unlocked_slots': start.get('unlocked_slots')})
    # v81 still validates the entire original start. No acquisition reward is
    # replayed and no terminal field is read here.
    result = previous.compile_start(row, **kwargs)
    if not any(e['fate_ids'] for e in entries):
        return result
    for i, entry in enumerate(entries):
        cards = result['battle']['players'][i]['cards']
        expected = [facts['raw_to_runtime'].get(str(x)) for x in entry['starting_raw_cards']]
        if expected != cards or type(entry['unlocked_slots']) is not int or entry['unlocked_slots'] != len(cards):
            raise UnresolvedBattle('scroll_opening_v82:explicit_grid_mapping_required')
        if entry['fate_ids']:
            declared = result['declared_components'][i]
            declared['preparation_fates_not_reapplied'] = [x for x in declared['preparation_fates_not_reapplied'] if x != 198]
            declared['fate198_acquisition_not_reapplied_opening_executed'] = True
    result['battle']['scroll_opening'] = {'players': entries}
    result['scroll_opening_v82_context'] = {
        'evidence_sha256': PROOF_SHA, 'ownership_from_start': True,
        'original_board_preserved': True, 'acquisition_reward_replayed': False,
        'battle_only_card_changes': True, 'training_label_allowed': False,
    }
    return result


def simulate_batch(battles, *, timeout=90):
    extension_contract()
    previous.extension_contract()
    # Preserve the cloud adapter's private compiler graph; override only the
    # runtime bridge, without assigning globals on frozen modules.
    result = isolated_compiler(previous.previous, runtime_bridge=BRIDGE).simulate_batch(battles, timeout=timeout)
    result['adapter_contract'] = {**result['adapter_contract'],
        'schema': 'complete-single-battle-diagnostic-v82', 'evidence_sha256': PROOF_SHA,
        'bound_cloud_parameter_extension': True, 'scroll_opening_extension': True}
    return result
