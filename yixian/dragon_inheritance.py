"""Explicit fate24 trigger ledger and pool-backed extra draws, mode3 only.

Both triggers draw from the merged sect/profession pool, confirmed by the user.
An external controller must signal the real trigger and supply legal candidates;
the first-round scheduling relative to ordinary draws is still unestablished.
Imported snapshots acknowledge prior events without replaying rewards.
"""
from collections.abc import Mapping
from copy import deepcopy
import hashlib
from pathlib import Path

from .pool_draw import RoundDrawProvider
from .research import canonical_json

CHARACTER = 1000003
IMPLEMENTED_INHERITANCE_COMPONENT_IDS = frozenset({24})
LEDGER = 'talent_24_draw_ledger'
PENDING = 'talent_24_pending_draw'
TRIGGERS = ('first_round', 'realm5')
DRAW_POOL = 'combined_remaining'
DRAW_RULE_VERSION = 2
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = 'data/inspection/dragon-inheritance-draw-v2.json'


class UnknownInheritanceState(ValueError):
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
    if 24 not in fates:
        if state.get(LEDGER) or state.get(PENDING):
            raise UnknownInheritanceState('Inheritance state exists without the owned fate')
        return result
    if result.get('character_id') != CHARACTER or result.get('is_mirror', False) is not False:
        raise UnknownInheritanceState('Only non-mirror Long Yao is implemented')
    if type(result.get('level')) is not int or not 1 <= result['level'] <= 6:
        raise UnknownInheritanceState('Explicit realm is required')
    if LEDGER in state:
        ledger = state[LEDGER]
        if (not isinstance(ledger, dict) or ledger.get('game_mode') != 3
                or ledger.get('origin') not in ('fresh_match', 'imported_snapshot')
                or not isinstance(ledger.get('events'), dict) or set(ledger['events']) != set(TRIGGERS)):
            raise ValueError('Invalid inheritance ledger')
        for entry in ledger['events'].values():
            if not isinstance(entry, dict) or entry.get('status') not in ('available', 'pending', 'completed', 'imported_snapshot'):
                raise ValueError('Invalid inheritance event status')
    if state.get(PENDING) is not None and not isinstance(state[PENDING], dict):
        raise ValueError('Invalid pending inheritance request')
    return result


def initialize_inheritance(player, *, fresh_match=False, snapshot_round=None, game_mode=3):
    result = _copy(player)
    if type(game_mode) is not int or game_mode != 3:
        raise UnknownInheritanceState('Only ordinary ranked mode3 is implemented; mode16 has different counts')
    if type(fresh_match) is not bool or (fresh_match and snapshot_round is not None):
        raise ValueError('Choose fresh match or explicit snapshot import')
    if 24 not in result.get('fates', []):
        return result
    if not fresh_match and (type(snapshot_round) is not int or snapshot_round < 1):
        raise UnknownInheritanceState('Snapshot round must be explicit')
    state = result['effect_state']
    if LEDGER in state:
        # Simulation history always wins; a future snapshot cannot refill or
        # silently complete a pending simulated reward.
        return result
    if fresh_match and result['level'] != 1:
        raise UnknownInheritanceState('Fresh-match initialization requires realm1')
    events = {trigger: {'status': 'available'} for trigger in TRIGGERS}
    if not fresh_match:
        events['first_round'] = {'status': 'imported_snapshot', 'source_round': snapshot_round}
        if result['level'] >= 5:
            events['realm5'] = {'status': 'imported_snapshot', 'source_round': snapshot_round}
    state[LEDGER] = {'game_mode': 3, 'origin': 'fresh_match' if fresh_match else 'imported_snapshot', 'events': events}
    return result


def request_inheritance_draw(player, trigger, *, round_number, previous_level=None, pool_category=None):
    result = _copy(player)
    if type(round_number) is not int or round_number < 1 or trigger not in TRIGGERS:
        raise ValueError('Explicit trigger and positive round are required')
    if pool_category not in (None, DRAW_POOL):
        raise ValueError('Fate24 always draws from the combined sect/profession pool')
    state = result['effect_state']
    if LEDGER not in state:
        raise UnknownInheritanceState('Initialize or import the fate24 ledger first')
    entry = state[LEDGER]['events'][trigger]
    if entry['status'] in ('completed', 'imported_snapshot'):
        return result
    if trigger == 'first_round' and (round_number != 1 or result['level'] != 1):
        raise UnknownInheritanceState('The first-round reward cannot be reconstructed in a later preparation')
    if trigger == 'realm5' and (type(previous_level) is not int or previous_level != 4 or result['level'] != 5):
        raise UnknownInheritanceState('An explicit realm4-to5 transition is required')
    if trigger == 'realm5' and state[LEDGER]['events']['first_round']['status'] not in ('completed', 'imported_snapshot'):
        raise UnknownInheritanceState('First-round history must be settled or explicitly imported')
    if not isinstance(result.get('id'), str) or not result['id']:
        raise UnknownInheritanceState('A stable match-local player id is required')
    hand = result.get('hand_cards')
    if not isinstance(hand, list) or any(type(x) is not int or x == 0 or x < -1 for x in hand):
        raise UnknownInheritanceState('An explicit raw-card hand is required')
    identity = hashlib.sha256(canonical_json([result['id'], trigger]).encode()).hexdigest()
    request = {'effect_id': 24, 'kind': 'draw_inheritance_cards', 'trigger': trigger,
               'event_key': 'fate24:'+identity, 'round': round_number, 'realm': result['level'],
               'pool': DRAW_POOL, 'rules_version': DRAW_RULE_VERSION,
               'count': 2, 'hand_before': list(hand), 'hand_overflow_exempt': True}
    if state.get(PENDING) is not None:
        if state[PENDING] != request:
            raise UnknownInheritanceState('Resolve the existing inheritance request before another trigger')
        return result
    if entry['status'] == 'pending':
        raise UnknownInheritanceState('Pending ledger is missing its request')
    state[PENDING] = request
    entry['status'] = 'pending'
    return result


def resolve_inheritance_draw(player, draw_provider=None, *, pool_category=None):
    result = _copy(player)
    if pool_category not in (None, DRAW_POOL):
        raise ValueError('Fate24 always draws from the combined sect/profession pool')
    state = result['effect_state']
    request = state.get(PENDING)
    if request is None:
        return {'player': result, 'events': [], 'pending_actions': [], 'complete_resolution': True}
    expected_key = 'fate24:'+hashlib.sha256(canonical_json([result.get('id'), request.get('trigger')]).encode()).hexdigest()
    if (LEDGER not in state or request.get('trigger') not in TRIGGERS
            or state[LEDGER]['events'][request['trigger']]['status'] != 'pending'
            or request.get('effect_id') != 24 or request.get('kind') != 'draw_inheritance_cards'
            or request.get('event_key') != expected_key or request.get('pool') != DRAW_POOL
            or type(request.get('rules_version')) is not int or request['rules_version'] != DRAW_RULE_VERSION
            or type(request.get('round')) is not int or request['round'] < 1
            or request.get('hand_overflow_exempt') is not True
            or request.get('count') != 2 or request.get('realm') != result['level']
            or request.get('hand_before') != result.get('hand_cards')):
        raise UnknownInheritanceState('Pending draw boundary or rule version changed; legacy requests require explicit migration')
    if draw_provider is None:
        pending = deepcopy(request)
        pending['reason'] = 'pool_provider_required'
        return {'player': result, 'events': [], 'pending_actions': [pending], 'complete_resolution': False}
    if not isinstance(draw_provider, RoundDrawProvider):
        raise ValueError('Use the pool-backed provider with persistent draw receipts')
    observation = {'round': request['round'], 'self': {k: deepcopy(result[k]) for k in
                   ('id', 'character_id', 'level', 'career', 'hand_cards', 'cards', 'fates') if k in result}}
    requests = [{'pool': request['pool'], 'count': 2, 'source': 'fate24', 'trigger': request['trigger']}]
    cards = draw_provider.draw_once(request['event_key'], requests, observation)
    result['hand_cards'].extend(cards)
    state[LEDGER]['events'][request['trigger']] = {'status': 'completed', 'round': request['round'],
                                                  'cards': list(cards), 'event_key': request['event_key'],
                                                  'pool': DRAW_POOL, 'rules_version': DRAW_RULE_VERSION}
    state.pop(PENDING)
    event = {'phase': 'fate_extra_draw', 'effect_id': 24, 'trigger': request['trigger'], 'cards': cards,
             'event_key': request['event_key'], 'pool_receipt_reused': not bool(draw_provider.last_events()),
             'pool': request['pool'], 'cultivation_gain': 0, 'hand_overflow_exempt': True,
             'pool_audit': draw_provider.last_events(), 'original_actions_reconstructed': False}
    return {'player': result, 'events': [event], 'pending_actions': [], 'complete_resolution': True}


def contract():
    return {'schema_version': 2, 'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'evidence': EVIDENCE, 'evidence_sha256': hashlib.sha256((ROOT/EVIDENCE).read_bytes()).hexdigest(),
            'character_id': CHARACTER, 'game_mode': 3, 'draw_counts': {'first_round': 2, 'realm5': 2},
            'draw_provider_sha256': hashlib.sha256((ROOT/'yixian/pool_draw.py').read_bytes()).hexdigest(),
            'pool_category': DRAW_POOL, 'pool_category_source': 'explicit_user_confirmation_2026_11_12',
            'normal_draw_overflow_applies': False, 'overflow_scope': 'ordinary_round_start_only',
            'legacy_pending_request_policy': 'reject_missing_or_old_rule_version_without_explicit_migration',
            'snapshot_import_replays_rewards': False, 'initial_relative_draw_order_verified': False,
            'automatic_flow_hook_available': False, 'full_match_resume_available': False,
            'current_server_rules_verified': False, 'scope': 'explicit_trigger_with_confirmed_combined_pool_component'}
