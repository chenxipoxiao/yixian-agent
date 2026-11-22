"""Resumable reward phase after destiny has already been settled once.

Only explicit raw-card Dragon Scale rewards are dispatched here. This phase
cannot invoke combat or deduct destiny. Random outcomes belong to the caller's
environment, and unresolved death rewards must finish before this phase starts.
It is not a checkpoint/resume implementation for the entire eight-player match.
"""
from collections.abc import Mapping
from copy import deepcopy
import hashlib
from pathlib import Path

from .dragon_scale_reward import apply_post_battle_upgrade, contract as reward_contract
from .research import canonical_json


def contract():
    return {'schema_version': 1, 'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'reward': reward_contract(), 'scope': 'explicit_post_settlement_reward_phase',
            'deducts_destiny': False, 'random_outcomes': 'environment_supplied_slot',
            'full_match_resume_available': False, 'current_server_rules_verified': False}


def _fingerprint(value):
    return hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()


def _seal(phase):
    phase['state_sha256'] = _fingerprint({k: v for k, v in phase.items() if k != 'state_sha256'})
    return phase


def begin_post_battle_phase(players, *, battle_id):
    """Freeze both already-settled players; the phase is safe to JSON-serialize."""
    if not isinstance(battle_id, str) or not battle_id:
        raise ValueError('An explicit battle id is required')
    if not isinstance(players, (list, tuple)) or len(players) != 2:
        raise ValueError('Exactly two settled players are required')
    copied = deepcopy(list(players))
    canonical_json(copied)
    identifiers = []
    for player in copied:
        if not isinstance(player, dict) or not isinstance(player.get('id'), str) or not player['id']:
            raise ValueError('Each player requires a stable id')
        if type(player.get('life')) is not int or not isinstance(player.get('cards'), list):
            raise ValueError('Already settled destiny and explicit raw board are required')
        if not isinstance(player.get('fates', []), list) or not isinstance(player.get('effect_state'), dict):
            raise ValueError('Initialized effect state and fates are required')
        if player['effect_state'].get('death_fate_pending'):
            raise ValueError('Resolve death rewards before starting the post-battle phase')
        identifiers.append(player['id'])
    if len(set(identifiers)) != 2:
        raise ValueError('Player ids must be distinct')
    return _seal({'schema_version': 1, 'battle_id': battle_id, 'contract': contract(),
                  'players': copied, 'completed_players': [], 'selected_slots': {},
                  'card_catalog_sha256': None,
                  'pending_actions': [], 'events': [], 'complete_resolution': False})


def resolve_post_battle_phase(phase, card_catalog, *, selected_slots=None):
    """Continue only rewards; completed players and identical retries are no-ops.

    The seal catches accidental edits between serialization and continuation;
    it is a consistency check, not authentication of externally supplied state.
    """
    if not isinstance(phase, Mapping) or phase.get('schema_version') != 1:
        raise ValueError('Unknown post-battle phase schema')
    if phase.get('state_sha256') != _fingerprint({k: v for k, v in phase.items() if k != 'state_sha256'}):
        raise ValueError('Post-battle phase changed after it was frozen')
    if phase.get('contract') != contract():
        raise ValueError('Post-battle contract changed; exact continuation is unavailable')
    result = deepcopy(dict(phase))
    if not isinstance(card_catalog, Mapping) or any(type(key) is not int for key in card_catalog):
        raise ValueError('Raw-card metadata must use integer ids')
    catalog_sha = _fingerprint([[key, card_catalog[key]] for key in sorted(card_catalog)])
    if result['card_catalog_sha256'] is not None and result['card_catalog_sha256'] != catalog_sha:
        raise ValueError('Card metadata changed during the reward phase')
    result['card_catalog_sha256'] = catalog_sha
    choices = {} if selected_slots is None else selected_slots
    if not isinstance(choices, Mapping) or any(type(v) is not int for v in choices.values()):
        raise ValueError('Environment choices must map player ids to integer slots')
    identifiers = {p['id'] for p in result['players']}
    if any(identifier not in identifiers for identifier in choices):
        raise ValueError('Choice refers to a player outside this battle')
    new_events = []
    pending = []
    for player in result['players']:
        identifier = player['id']
        if identifier in result['completed_players']:
            if identifier in choices and choices[identifier] != result['selected_slots'].get(identifier):
                raise ValueError('A completed reward cannot be changed')
            continue
        owns_dragon_scale = any(type(x) is int and x == 27 for x in player.get('fates', []))
        if not owns_dragon_scale:
            if identifier in choices:
                raise ValueError('Player has no Dragon Scale reward')
            result['completed_players'].append(identifier)
            continue
        reward_player = deepcopy(player)
        # Flow supports explicit fixture ids as well. Other fates are retained
        # on the player; this component only handles the owned numeric fate 27.
        reward_player['fates'] = [27]
        reward_player['board'] = deepcopy(player['cards'])
        reward = apply_post_battle_upgrade(reward_player, card_catalog, selected_slot=choices.get(identifier))
        player['cards'] = reward['player']['board']
        player['effect_state'] = reward['player']['effect_state']
        new_events.extend(dict(event, player=identifier, battle_id=result['battle_id']) for event in reward['events'])
        pending.extend(dict(action, player=identifier, battle_id=result['battle_id']) for action in reward['pending_actions'])
        if reward['complete_resolution']:
            result['completed_players'].append(identifier)
            if identifier in choices:
                result['selected_slots'][identifier] = choices[identifier]
    result['events'].extend(new_events)
    result['pending_actions'] = pending
    result['complete_resolution'] = len(result['completed_players']) == 2
    return {'phase': _seal(result), 'new_events': new_events}
