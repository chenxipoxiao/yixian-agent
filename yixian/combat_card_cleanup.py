"""Guarded suffix of card0 OnAfterExecuted, not a whole card executor.

This starts *after* post-card effects, adjacency and category bookkeeping.
The caller must explicitly attest that boundary; a hit result alone does not
establish it. Candidate changes never advance the actor-turn state machine.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .combat_initialization import ROOT, IncompleteCombatState
from .combat_death_guard import _players
from .combat_attack_calculation import CONTEXT_FIELDS, _integer
from .combat_hit import ALLOWED_BUFFS as HIT_BUFFS, load_hit_contract

EVIDENCE = 'data/inspection/card-cleanup-v1.json'
EVIDENCE_HASH = 'd6c0037392f52b667b0537a215080f944f7b6cbb2b762e96dde149aee7456b23'
BOUNDARY = 'on_after_executed_after_category_bookkeeping'
ALLOWED_BUFFS = HIT_BUFFS | frozenset(map(str, (228, 307, 478, 729, 644, 363, 330, 382)))


def load_card_cleanup_contract(root=ROOT):
    raw = (Path(root)/EVIDENCE).read_bytes()
    if hashlib.sha256(raw).hexdigest() != EVIDENCE_HASH:
        raise ValueError('Card cleanup evidence hash mismatch')
    evidence = json.loads(raw)
    hit = load_hit_contract(root)
    client_hash = hit['attack_calculation_contract']['action_boundary_contract']['death_guard_contract']['client_dll_sha256']
    if evidence['client_dll_sha256'] != client_hash:
        raise ValueError('Card cleanup and hit client versions differ')
    return {'schema_version': 1, 'scope': evidence['scope'],
            'evidence_sha256': EVIDENCE_HASH,
            'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'client_dll_sha256': evidence['client_dll_sha256'], 'hit_contract': hit,
            'boundary': BOUNDARY, 'effective_card_id': 0, 'game_mode_scope': 3,
            'allowed_cleanup_buff_ids': sorted(map(int, ALLOWED_BUFFS)),
            'context_policy': 'explicit complete empty selections, resonance0, explicit prior-hook boundary',
            'candidate_transaction_only': True, 'whole_post_card_hook_completed': False,
            'action_phase_reply_available': False, 'server_parity_verified': False,
            'training_label_allowed': False, 'settlement_allowed': False}


def resolve_normal_card_cleanup(players, *, actor_index, card_item, checkpoint, game_mode=3):
    """Resolve only the pinned OnAfterExecuted suffix at an explicit boundary.

    card_item refers to the actual executing item, including its had_used flag.
    No missing context is filled from replay defaults. This function does not
    check or execute preceding hooks and cannot certify an entire action.
    """
    if type(game_mode) is not int or game_mode != 3:
        raise IncompleteCombatState('Only ordinary mode3 is scoped')
    _integer(actor_index, 'actor_index', 0, 1)
    if not isinstance(card_item, Mapping):
        raise IncompleteCombatState('Explicit card item required')
    _integer(card_item.get('effective_card_id'), 'card_item.effective_card_id')
    if type(card_item.get('had_used')) is not bool:
        raise IncompleteCombatState('Explicit card_item.had_used boolean required')
    original = _players(players)
    original_item = deepcopy(dict(card_item))
    candidate = deepcopy(original); item = deepcopy(original_item); events = []
    contract = load_card_cleanup_contract()
    body = {'players': original, 'actor_index': actor_index, 'card_item': original_item,
            'checkpoint': checkpoint, 'game_mode': game_mode, 'contract': contract}
    input_hash = hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True,
                                          separators=(',', ':'), allow_nan=False).encode()).hexdigest()

    def report(resolved, reason=None):
        return {'cleanup_resolved': resolved, 'blocked_reason': reason,
                'input_sha256': input_hash, 'contract': contract,
                'candidate_players': deepcopy(candidate if resolved else original),
                'candidate_card_item': deepcopy(item if resolved else original_item),
                'candidate_events': deepcopy(events) if resolved else [],
                'state_committed': False, 'preceding_hooks_verified_by_this_component': False,
                'whole_post_card_hook_completed': False, 'action_completed': False,
                'action_phase_reply_available': False, 'server_parity_verified': False,
                'training_label_allowed': False, 'settlement_allowed': False, 'winner_index': None}

    if (not isinstance(checkpoint, Mapping) or checkpoint.get('boundary') != BOUNDARY
            or checkpoint.get('preceding_hooks_resolved') is not True):
        return report(False, 'missing_explicit_cleanup_boundary')
    if item['effective_card_id'] != 0:
        return report(False, 'unsupported_effective_card')
    if item.get('card_config_overrides'):
        return report(False, 'dynamic_card_item_override')
    for index, player in enumerate(candidate):
        if player.get('card_config_overrides'):
            return report(False, 'dynamic_card_config_override:'+str(index))
        context = player.get('attack_context')
        if (not isinstance(context, Mapping) or context.get('complete') is not True
                or any(k not in context for k in CONTEXT_FIELDS)):
            return report(False, 'missing_complete_effect_context:'+str(index))
        for key in CONTEXT_FIELDS:
            values = context[key]
            if not isinstance(values, list):
                raise IncompleteCombatState('Explicit ID list required: '+key)
            for value in values:
                _integer(value, key, 1)
            if values:
                return report(False, 'unsupported_nonempty_'+key+':'+str(index))
        resonance = player.get('resonance_context')
        if not isinstance(resonance, Mapping) or any(k not in resonance for k in ('selected_id', 'round', 'realm')):
            return report(False, 'missing_explicit_resonance_context:'+str(index))
        selected = _integer(resonance['selected_id'], 'resonance.selected_id')
        _integer(resonance['round'], 'resonance.round', 1)
        _integer(resonance['realm'], 'resonance.realm', 0, 6)
        if selected != 0:
            return report(False, 'unsupported_resonance_selection:'+str(index))
        unknown = set(player['raw_buffs']) - ALLOWED_BUFFS
        if unknown:
            return report(False, 'unsupported_cleanup_buffs:'+str(index)+':'+','.join(sorted(unknown, key=int)))

    buffs = candidate[actor_index]['raw_buffs']

    def remove(key):
        if key in buffs:
            before = buffs.pop(key)
            events.append({'player_index': actor_index, 'buff_id': int(key),
                           'operation': 'remove', 'before': before, 'after': None})

    def modify(key, delta):
        # These supported IDs have no reached secondary ModifyBuffValue hooks
        # in the explicit scope above. Preserve native no-op/removal semantics.
        if delta == 0 or (delta < 0 and key not in buffs):
            return
        before = buffs.get(key); value = buffs.get(key, 0) + delta
        if abs(value) > 1_000_000:
            raise IncompleteCombatState('Candidate counter outside supported bounds: '+key)
        if value <= 0:
            buffs.pop(key, None)
        else:
            buffs[key] = value
        events.append({'player_index': actor_index, 'buff_id': int(key), 'operation': 'modify',
                       'requested_delta': delta, 'before': before, 'after': buffs.get(key)})

    if '306' in buffs:
        if '228' in buffs:
            modify('228', -1)
        else:
            modify('6', -buffs['306'])
        remove('306')
    if '307' in buffs:
        gain = buffs['307']
        if buffs.get('478', 0) > 0:
            gain += buffs['478']; remove('478')
        if gain > 0:
            modify('6', gain)
        remove('307')
    remove('729')
    modify('644', buffs.get('302', 0))
    remove('302'); remove('303')
    previous_used = item['had_used']; item['had_used'] = True
    events.append({'player_index': actor_index, 'event': 'card_item_used',
                   'before': previous_used, 'after': True})
    # Pinned card0 name contains no elemental token; its cardType is0.
    remove('330')
    modify('363', 1)
    remove('382')
    return report(True)
