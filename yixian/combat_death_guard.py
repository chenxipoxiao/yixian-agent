"""Isolated client death-guard boundaries; not a full combat or label source.

The scheduler must supply actual action-boundary state. These helpers never
derive initiative from permanent17 or restore it after consumption.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .combat_initialization import ROOT, IncompleteCombatState, _int_field
from .combat_permanent import derive_permanent_combat_state, load_permanent_initialization_contract

EVIDENCE = 'data/inspection/death-guard-v1.json'
EVIDENCE_HASH = '3296e91de96b317aecb0b7d31a158e32ae9d87b89eaf5a8d3cbc1ca3188b8bcc'
OPENING_BOUNDARY = 'OnBattleStarted.after_initial17_before_remaining_hooks'
TURN_END_BOUNDARY = 'OnTurnEnded.buff18_cleanup'


def _mode(game_mode):
    if type(game_mode) is not int or game_mode != 3:
        raise IncompleteCombatState('Death guard scoped to explicit ordinary mode3')


def _limits():
    return {'complete_battle_input': False, 'full_action_scheduler_available': False,
            'server_parity_verified': False, 'counterfactual_safe': False,
            'training_label_allowed': False, 'settlement_allowed': False}


def load_death_guard_contract(root=ROOT):
    raw = (Path(root)/EVIDENCE).read_bytes()
    if hashlib.sha256(raw).hexdigest() != EVIDENCE_HASH:
        raise ValueError('Death guard evidence hash mismatch')
    evidence = json.loads(raw)
    permanent = load_permanent_initialization_contract(root)
    if evidence['client_dll_sha256'] != permanent['base_initialization']['client_dll_sha256']:
        raise ValueError('Death guard client versions differ')
    return dict(_limits(), schema_version=1, scope=evidence['scope'], game_mode_scope=3,
                evidence_sha256=EVIDENCE_HASH, client_dll_sha256=evidence['client_dll_sha256'],
                implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                permanent_initialization=permanent, opening_boundary=OPENING_BOUNDARY,
                cleanup_boundary=TURN_END_BOUNDARY, buff_presence='dictionary_key',
                death_check_order='left_then_right_with_short_circuit',
                original_action_trajectories_reconstructed=False)


def derive_death_guard_opening(public_data, *, game_mode=3):
    """Fresh snapshot reconstruction only, never an update of an ongoing battle."""
    _mode(game_mode)
    result = derive_permanent_combat_state(public_data, game_mode=game_mode)
    combat = deepcopy(result['initialized_combat'])
    raw = result['permanent_input'].get('17', 0)
    if raw > 0:
        combat['raw_buffs']['17'] = raw
    # Keep the earlier boundary for audit, but never leave processed17 queued
    # as a pending hook at this later boundary (including an explicit zero).
    result['initdata_deferred_permanent_entries'] = deepcopy(result['deferred_permanent_entries'])
    result['deferred_permanent_entries'].pop('17', None)
    result.update(_limits())
    result.update(scope='candidate_initial17_opening_boundary', guard_opening_combat=combat,
                  boundary=OPENING_BOUNDARY, guard17_source_value=raw,
                  guard17_applied_value=max(0, raw), initiative_inferred_from_guard=False,
                  complete_opening_effects_applied=False,
                  pending_before_battle=['remaining_OnBattleStarted_hooks', 'ordinary_and_seasonal_interactions',
                                        'action_scheduler', 'snapshot_timing_calibration'])
    result['initialization_events'].append({'source': 'lastRoundData.permanentBuffTempDatas',
                                           'buff_id': 17, 'raw_value': raw, 'applied_value': max(0, raw),
                                           'hp_delta': 0, 'boundary': OPENING_BOUNDARY})
    return result


def _players(players):
    if not isinstance(players, (list, tuple)) or len(players) != 2:
        raise IncompleteCombatState('Exactly two ordered boundary states required')
    copied = []
    for player in players:
        if not isinstance(player, Mapping):
            raise IncompleteCombatState('Explicit boundary state required')
        _int_field(player, 'hp')
        buffs = player.get('raw_buffs')
        if not isinstance(buffs, Mapping):
            raise IncompleteCombatState('Explicit combat raw_buffs required; no permanent-map fallback')
        for key, value in buffs.items():
            if (not isinstance(key, str) or not key.isascii() or not key.isdecimal()
                    or str(int(key)) != key or int(key) <= 0
                    or type(value) is not int or abs(value) > 1_000_000):
                raise IncompleteCombatState('Malformed combat buff map')
        state = deepcopy(dict(player)); state['raw_buffs'] = dict(buffs)
        copied.append(state)
    return copied


def _check_one(player, index, events):
    buffs = player['raw_buffs']
    if player['hp'] <= 0 and '17' in buffs:
        value = buffs.get('18', 0) + 1
        if abs(value) > 1_000_000:
            raise IncompleteCombatState('Out-of-scope death guard value')
        if value > 0:
            buffs['18'] = value
        else:
            buffs.pop('18', None)
        consumed = buffs.pop('17')
        events.append({'player_index': index, 'event': 'consume17_add18',
                       'removed17_value': consumed, 'buff18_value': buffs.get('18'), 'hp_delta': 0})
    return '18' in buffs


def check_death_boundary(players, *, game_mode=3):
    """Mirror DeathCheck's boolean and side effects, without selecting a winner.

    Slots are the client's left/right order, not first/second actor. In particular
    do not evaluate both CheckSiZhan calls eagerly: the first can short-circuit.
    """
    _mode(game_mode)
    states = _players(players); events = []; checked = []
    for index in (0, 1):
        checked.append(index)
        active = _check_one(states[index], index, events)
        if active and states[index]['hp'] <= states[1-index]['hp']:
            return dict(_limits(), scope='candidate_client_DeathCheck_boundary', players=states,
                        events=events, checked_player_indices=checked, candidate_death_check=False,
                        deferred_by_player_index=index, winner_index=None, hp_was_clamped=False)
    return dict(_limits(), scope='candidate_client_DeathCheck_boundary', players=states,
                events=events, checked_player_indices=checked,
                candidate_death_check=any(p['hp'] <= 0 for p in states),
                deferred_by_player_index=None, winner_index=None, hp_was_clamped=False)


def cleanup_guard_at_turn_end(players, *, actor_index, boundary, game_mode=3):
    """Run only the named owner's cleanup hook, after preceding turn-end hooks.

    This is not a card-end/extra-action-end callback. Remaining turn-end effects
    must run before the scheduler invokes the following DeathCheck.
    """
    _mode(game_mode)
    if type(actor_index) is not int or actor_index not in (0, 1) or boundary != TURN_END_BOUNDARY:
        raise IncompleteCombatState('Explicit actor and OnTurnEnded buff18 cleanup boundary required')
    states = _players(players)
    buffs = states[actor_index]['raw_buffs']; removed = buffs.pop('18', None)
    events = [] if removed is None else [{'player_index': actor_index, 'event': 'remove18_at_owner_turn_end',
                                         'removed18_value': removed, 'hp_delta': 0}]
    return dict(_limits(), scope='candidate_owner_turn_end_guard_cleanup', players=states, events=events,
                boundary=TURN_END_BOUNDARY, actor_index=actor_index,
                remaining_turn_end_hooks_required=True, following_death_check_required=True)
