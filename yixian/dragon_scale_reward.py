"""Long Yao's post-battle upgrade on explicit state and explicit random choice.

This is a separate, conditional reward component. It does not deduct destiny,
reconstruct preparation actions, choose a random distribution, or certify full
server rules. A caller must supply already settled destiny and resolve pending
selection before advancing the match. Raw counters are imported only once.
"""
from collections.abc import Mapping
from copy import deepcopy
import hashlib
from pathlib import Path

from .research import canonical_json

CHARACTER = 1000003
EXCLUSIVE_CARDS = frozenset({15, 16})
REMAINING = 'talent_27_upgrade_remaining'
PENDING = 'talent_27_upgrade_pending'


class UnknownDragonScaleReward(ValueError):
    pass


def _copy(player):
    if not isinstance(player, Mapping):
        raise ValueError('Player must be an object')
    canonical_json(player)
    result = deepcopy(dict(player))
    fates = result.get('fates', [])
    if not isinstance(fates, list) or any(type(x) is not int for x in fates):
        raise ValueError('Explicit numeric fates are required')
    state = result.setdefault('effect_state', {'schema_version': 1})
    if not isinstance(state, dict) or type(state.get('schema_version')) is not int or state['schema_version'] != 1:
        raise ValueError('Unknown effect state schema')
    if REMAINING in state and (type(state[REMAINING]) is not int or state[REMAINING] not in (0, 1)):
        raise ValueError('Upgrade remaining uses must be 0 or 1')
    if state.get(PENDING) is not None and not isinstance(state[PENDING], dict):
        raise ValueError('Invalid pending upgrade')
    return result


def initialize_reward(player, *, talent_counters=None, newly_acquired=False):
    result = _copy(player)
    if type(newly_acquired) is not bool:
        raise ValueError('New acquisition marker must be boolean')
    if talent_counters is not None and not isinstance(talent_counters, Mapping):
        raise ValueError('Raw counters must be a mapping')
    if 27 not in result.get('fates', []):
        if newly_acquired:
            raise ValueError('Newly acquired Dragon Scale must already be owned')
        return result
    if result.get('character_id') != CHARACTER:
        raise UnknownDragonScaleReward('This reward component is scoped to Long Yao')
    if result.get('is_mirror', False) is not False:
        raise UnknownDragonScaleReward('Mirror reward state is outside this component')
    state = result['effect_state']
    if REMAINING not in state:
        if newly_acquired:
            state[REMAINING] = 1
        else:
            if talent_counters is None or '27' not in talent_counters:
                raise UnknownDragonScaleReward('Explicit raw talent27 counter or new acquisition required')
            raw = talent_counters['27']
            if type(raw) is not int or raw not in (0, 1):
                raise ValueError('Raw talent27 counter must be 0 or 1')
            state[REMAINING] = raw
    return result


def upgrade_candidates(board, card_catalog):
    """Return board slots, retaining duplicates; prefer Long Yao's fate cards.

    IDs advance by 10000 in the pinned client CardItem.Upgrade method. Both
    source and destination rows are checked; absent/ambiguous metadata fails.
    The catalog is metadata, never a declaration of legal draw-pool membership.
    """
    if (not isinstance(board, list) or not 1 <= len(board) <= 8
            or any(type(card) is not int or card < 0 for card in board)):
        raise ValueError('Provide one to eight raw board slots; zero means empty')
    if not isinstance(card_catalog, Mapping):
        raise ValueError('Explicit card metadata is required')
    candidates = []
    for slot, identifier in enumerate(board):
        if identifier == 0:
            continue
        row = card_catalog.get(identifier)
        if not isinstance(row, Mapping) or row.get('id') != identifier:
            raise UnknownDragonScaleReward(f'Missing card metadata: {identifier}')
        if type(row.get('rarity')) is not int or type(row.get('noUpgrade')) is not bool:
            raise UnknownDragonScaleReward('Missing rarity or upgradeability metadata')
        if row['rarity'] != 0 or row['noUpgrade']:
            continue
        if (not isinstance(row.get('name'), str) or not row['name']
                or any(type(row.get(key)) is not int for key in ('owner', 'level', 'sect', 'career'))):
            raise UnknownDragonScaleReward('Missing card family or owner metadata')
        upgraded = card_catalog.get(identifier + 10000)
        if (not isinstance(upgraded, Mapping) or upgraded.get('id') != identifier + 10000
                or upgraded.get('rarity') != 1 or
                any(row.get(key) != upgraded.get(key) for key in ('name', 'owner', 'level', 'sect', 'career'))):
            raise UnknownDragonScaleReward(f'Unverified upgrade target: {identifier}')
        exclusive = identifier in EXCLUSIVE_CARDS
        if exclusive and row.get('owner') != CHARACTER:
            raise UnknownDragonScaleReward('Exclusive card ownership mismatch')
        candidates.append({'slot': slot, 'before_card': identifier, 'after_card': identifier + 10000,
                           'exclusive': exclusive})
    preferred = [c for c in candidates if c['exclusive']]
    return preferred or candidates


def apply_post_battle_upgrade(player, card_catalog, *, selected_slot=None):
    """Apply one legal upgrade, or return a pending request for an explicit draw.

    Missing randomness is never replaced by a preferred deterministic slot.
    A singleton is deterministic. No candidates preserve the charge. Existing
    simulation ledger wins over future replay snapshots and repeated calls.
    """
    result = initialize_reward(player)
    if selected_slot is not None and type(selected_slot) is not int:
        raise ValueError('Selected slot must be an integer')
    state = result['effect_state']
    if 27 not in result.get('fates', []):
        if selected_slot is not None:
            raise ValueError('Cannot select an upgrade for an unowned fate')
        return {'player': result, 'events': [], 'pending_actions': [], 'complete_resolution': True}
    life = result.get('life')
    if type(life) is not int:
        raise UnknownDragonScaleReward('Already settled destiny is required')
    if state[REMAINING] == 0 or life > 20:
        if selected_slot is not None or state.get(PENDING):
            raise ValueError('Upgrade is not currently available')
        return {'player': result, 'events': [], 'pending_actions': [], 'complete_resolution': True}
    candidates = upgrade_candidates(result.get('board'), card_catalog)
    request = {'effect_id': 27, 'kind': 'select_dragon_scale_upgrade_slot',
               'board': list(result['board']), 'candidate_slots': [c['slot'] for c in candidates]}
    if state.get(PENDING) is not None and state[PENDING] != request:
        raise UnknownDragonScaleReward('Board or candidate set changed while upgrade is pending')
    if not candidates:
        if selected_slot is not None:
            raise ValueError('No upgradable board card')
        return {'player': result, 'events': [{'phase': 'battle_end_upgrade', 'effect_id': 27,
                'status': 'no_eligible_board_card', 'remaining_uses_after': 1}],
                'pending_actions': [], 'complete_resolution': True}
    if selected_slot is None and len(candidates) > 1:
        state[PENDING] = request
        return {'player': result, 'events': [], 'pending_actions': [request], 'complete_resolution': False}
    slot = candidates[0]['slot'] if selected_slot is None else selected_slot
    chosen = next((candidate for candidate in candidates if candidate['slot'] == slot), None)
    if chosen is None:
        raise ValueError('Selected slot is outside the eligible priority group')
    result['board'][slot] = chosen['after_card']
    state[REMAINING] = 0
    state.pop(PENDING, None)
    event = {'phase': 'battle_end_upgrade', 'effect_id': 27, **chosen,
             'remaining_uses_before': 1, 'remaining_uses_after': 0}
    return {'player': result, 'events': [event], 'pending_actions': [], 'complete_resolution': True}


def contract():
    return {'schema_version': 1, 'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'scope': 'longyao_post_battle_reward_on_explicit_state', 'character_id': CHARACTER,
            'threshold': 20, 'raw_counter_mapping': {'0': 'unavailable', '1': 'available'},
            'exclusive_base_cards': sorted(EXCLUSIVE_CARDS), 'candidate_zone': 'board_only',
            'multiple_candidates': 'explicit_selection_required_no_random_distribution_claim',
            'no_candidates': 'retain_charge', 'life_already_settled_by_caller': True,
            'full_match_integration_complete': False, 'current_server_rules_verified': False}
