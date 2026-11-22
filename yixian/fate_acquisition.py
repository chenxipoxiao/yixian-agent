"""One-time Long Yao card grants from explicit new acquisitions.

Snapshot ownership is acknowledged without generating a card: a snapshot is
not an acquisition action. Missing prior actions, candidate eligibility, auto
arrangement and the granted cards' combat effects are outside this component.
"""
from collections.abc import Mapping
from copy import deepcopy
import hashlib
from pathlib import Path

from .research import canonical_json

CHARACTER = 1000003
GRANTS = {85: (15, 4), 86: (16, 5)}
IMPLEMENTED_ACQUISITION_FATE_IDS = frozenset(GRANTS)
LEDGER = 'longyao_card_acquisition_receipts'
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = 'data/inspection/longyao-fate-acquisition-v1.json'


class UnknownAcquisitionState(ValueError):
    pass


def _copy(player):
    if not isinstance(player, Mapping):
        raise ValueError('Player must be an object')
    canonical_json(player)
    result = deepcopy(dict(player))
    fates = result.get('fates', [])
    if not isinstance(fates, list) or any(type(x) not in (int, str) for x in fates):
        raise ValueError('Explicit fate ids are required')
    state = result.setdefault('effect_state', {'schema_version': 1})
    if not isinstance(state, dict) or type(state.get('schema_version')) is not int or state['schema_version'] != 1:
        raise ValueError('Unknown effect state schema')
    ledger = state.setdefault(LEDGER, {})
    if not isinstance(ledger, dict):
        raise ValueError('Acquisition receipts must be an object')
    for key, receipt in ledger.items():
        if key not in ('85', '86') or not isinstance(receipt, dict):
            raise ValueError('Unknown acquisition receipt')
        fate = int(key)
        if (receipt.get('card_id') != GRANTS[fate][0] or type(receipt.get('quantity')) is not int
                or receipt['quantity'] != 1 or receipt.get('origin') not in ('new_acquisition', 'imported_snapshot')
                or not isinstance(receipt.get('source_ref'), str) or not receipt['source_ref']):
            raise ValueError('Incompatible acquisition receipt')
    return result


def owned_grant_fates(player):
    return sorted(x for x in set(player.get('fates', [])) if type(x) is int and x in GRANTS)


def unacknowledged_grant_fates(player, snapshot_fates):
    """Detect imports that cannot safely be overlaid onto a branched hand."""
    ledger = _copy(player)['effect_state'][LEDGER]
    if not isinstance(snapshot_fates, list):
        raise ValueError('Snapshot fates must be a list')
    return [x for x in owned_grant_fates({'fates': snapshot_fates}) if str(x) not in ledger]


def _actor(player, relevant):
    if relevant and player.get('character_id') != CHARACTER:
        raise UnknownAcquisitionState('These card grants are only implemented for Long Yao')
    if relevant and player.get('is_mirror', False) is not False:
        raise UnknownAcquisitionState('Mirror acquisition is not implemented')


def _source(source_ref):
    if not isinstance(source_ref, str) or not source_ref:
        raise ValueError('An explicit acquisition or snapshot source is required')


def import_fate_acquisition_state(player, *, source_ref):
    """Import ownership once, without asserting a reconstructed reward history."""
    result = _copy(player)
    _source(source_ref)
    owned = owned_grant_fates(result)
    _actor(result, owned)
    events = []
    for fate in owned:
        ledger = result['effect_state'][LEDGER]
        if str(fate) in ledger:
            continue
        ledger[str(fate)] = {'card_id': GRANTS[fate][0], 'quantity': 1,
                             'origin': 'imported_snapshot', 'source_ref': source_ref}
        events.append({'phase': 'fate_acquisition_import', 'effect_id': fate,
                       'source_ref': source_ref, 'cards_generated': 0,
                       'reward_delivery_verified': False, 'original_action_reconstructed': False})
    return {'player': result, 'events': events, 'pool_delta': 0}


def grant_acquired_fate_cards(player, newly_acquired_fates, card_catalog, *, source_ref):
    """Append one generated base card to hand per previously unhandled fate.

    The caller must validate and perform the actual fate selection first.
    Existing receipts win over retries, even after a card was used or removed.
    No pool access, automatic merging, placement or overflow conversion occurs.
    """
    result = _copy(player)
    _source(source_ref)
    if (not isinstance(newly_acquired_fates, (list, tuple))
            or any(type(x) is not int or x not in GRANTS for x in newly_acquired_fates)
            or len(set(newly_acquired_fates)) != len(newly_acquired_fates)):
        raise ValueError('Provide unique supported new-acquisition ids')
    if any(fate not in owned_grant_fates(result) for fate in newly_acquired_fates):
        raise ValueError('Newly acquired fate must already be owned')
    _actor(result, newly_acquired_fates)
    events = []
    for fate in newly_acquired_fates:
        ledger = result['effect_state'][LEDGER]
        if str(fate) in ledger:
            continue
        card, realm = GRANTS[fate]
        row = card_catalog.get(card) if isinstance(card_catalog, Mapping) else None
        if (not isinstance(row, Mapping) or row.get('id') != card or row.get('owner') != CHARACTER
                or type(row.get('rarity')) is not int or row['rarity'] != 0
                or type(row.get('level')) is not int or row['level'] != realm
                or row.get('hidden') is not True or row.get('obsolete') is not False):
            raise UnknownAcquisitionState(f'Missing or incompatible base-card metadata: {card}')
        hand = result.get('hand_cards')
        if not isinstance(hand, list) or any(type(x) is not int or x == 0 or x < -1 for x in hand):
            raise UnknownAcquisitionState('An explicit raw-card hand is required for a new grant')
        before = len(hand)
        hand.append(card)
        ledger[str(fate)] = {'card_id': card, 'quantity': 1, 'origin': 'new_acquisition', 'source_ref': source_ref}
        events.append({'phase': 'fate_acquisition', 'effect_id': fate, 'source_ref': source_ref,
                       'card_id': card, 'quantity': 1, 'destination': 'hand', 'pool_delta': 0,
                       'hand_count_before': before, 'hand_count_after': len(hand),
                       'source': 'explicit_new_acquisition_not_reconstructed_replay'})
    return {'player': result, 'events': events, 'pool_delta': 0}


def contract():
    return {'schema_version': 1, 'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'evidence': EVIDENCE, 'evidence_sha256': hashlib.sha256((ROOT/EVIDENCE).read_bytes()).hexdigest(),
            'scope': 'explicit_longyao_one_time_fate_card_grants', 'character_id': CHARACTER,
            'grants': {str(k): {'card_id': v[0], 'quantity': 1} for k, v in GRANTS.items()},
            'destination': 'hand', 'pool_delta': 0, 'snapshot_import_generates_cards': False,
            'hand_overflow_converts_grant_to_cultivation': False, 'automatic_merge_or_placement': False,
            'candidate_eligibility_implemented': False, 'granted_card_combat_implemented_here': False,
            'current_server_rules_verified': False, 'original_replay_actions_reconstructed': False}
