"""Scoped ordinary-attack hit transaction; not a card or battle executor.

Consumes an environment-produced CalculateAttack packet. Input states are never
mutated. Returned candidates include HP/defense changes, but do not constitute an
action-phase reply, revival execution, a terminal result, or a training label.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .combat_initialization import ROOT, IncompleteCombatState
from .combat_attack_calculation import CONTEXT_FIELDS, ALLOWED_BUFFS as PREFIX_BUFFS
from .combat_attack_calculation import load_attack_calculation_contract
from .combat_death_guard import _players, _check_one
from .combat_resurrection import can_revive, load_resurrection_contract

EVIDENCE = 'data/inspection/combat-hit-v1.json'
EVIDENCE_HASH = '13eeaf75ac12cb64cb268a53eff08eb475a90dfc6fd3bc4f14d57aaa0e65ed46'
# Inert or handled in this exact type0 hit scope, NOT a whole-card whitelist.
ALLOWED_BUFFS = PREFIX_BUFFS | frozenset(map(str, (
    4, 5, 310, 433, 745, 598, 677, 302, 303, 324, 409, 351, 711,
    430, 612, 341, 231, 429, 597, 772)))


def _integer(value, name, minimum=0, maximum=1_000_000):
    if type(value) is not int or not minimum <= value <= maximum:
        raise IncompleteCombatState('Explicit bounded integer required: ' + name)
    return value


def load_hit_contract(root=ROOT):
    raw = (Path(root)/EVIDENCE).read_bytes()
    if hashlib.sha256(raw).hexdigest() != EVIDENCE_HASH:
        raise ValueError('Hit evidence hash mismatch')
    evidence = json.loads(raw)
    attack = load_attack_calculation_contract(root)
    revival = load_resurrection_contract(root)
    if evidence['client_dll_sha256'] != attack['action_boundary_contract']['death_guard_contract']['client_dll_sha256']:
        raise ValueError('Hit and attack client versions differ')
    return {'schema_version': 1, 'scope': evidence['scope'],
            'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'evidence_sha256': EVIDENCE_HASH, 'attack_calculation_contract': attack,
            'resurrection_contract': revival, 'allowed_hit_buff_ids': sorted(map(int, ALLOWED_BUFFS)),
            'game_mode_scope': 3, 'effective_card_id': 0, 'packet_type': 0,
            'required_scene_context': 'explicitly absent scene behavior; mutual default opponents',
            'complete_card_execution_available': False, 'full_battle_available': False,
            'server_parity_verified': False, 'training_label_allowed': False, 'settlement_allowed': False}


def resolve_normal_attack_hit(players, packet, *, effective_card_id, battle_context, game_mode=3):
    """Apply one supported packet to candidate states, atomically on success.

    Missing context is unresolved. Context attestations must be provided by the
    environment; an omitted replay field is not evidence of absence. The actual
    current card must be0, not a substitute for an unsupported attack card.
    """
    if type(game_mode) is not int or game_mode != 3:
        raise IncompleteCombatState('Only ordinary mode3 is scoped')
    _integer(effective_card_id, 'effective_card_id', maximum=2**31-1)
    original = _players(players)
    if not isinstance(packet, Mapping):
        raise IncompleteCombatState('Explicit damage packet required')
    required = ('source_index', 'target_index', 'type', 'damage', 'skip_wound_check', 'hit_def', 'feng_rui')
    if any(k not in packet for k in required):
        raise IncompleteCombatState('Incomplete damage packet')
    src = _integer(packet['source_index'], 'source_index', maximum=1)
    dst = _integer(packet['target_index'], 'target_index', maximum=1)
    if src == dst:
        raise IncompleteCombatState('Mutually opposing players required')
    _integer(packet['type'], 'packet.type', maximum=3)
    damage = _integer(packet['damage'], 'packet.damage', minimum=-1_000_000)
    _integer(packet['feng_rui'], 'packet.feng_rui', minimum=-1_000_000)
    for key in ('skip_wound_check', 'hit_def'):
        if type(packet[key]) is not bool:
            raise IncompleteCombatState('Explicit boolean required: ' + key)
    contract = load_hit_contract()
    body = {'players': original, 'packet': dict(packet), 'effective_card_id': effective_card_id,
            'battle_context': battle_context, 'contract': contract}
    digest = hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True,
                                      separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    candidate = deepcopy(original); events = []; final_packet = dict(packet)
    hp_loss = 0; def_loss = 0; guard_checked = False; revival_pending = False

    def report(success, reason=None):
        return {'hit_resolved': success, 'blocked_reason': reason, 'input_sha256': digest,
                'candidate_players': deepcopy(candidate if success else original),
                'candidate_events': deepcopy(events) if success else [],
                'settled_damage_packet': deepcopy(final_packet) if success else None,
                'hp_loss': hp_loss if success else None, 'def_loss': def_loss if success else None,
                'target_guard_checked': guard_checked if success else False,
                'revival_pending': revival_pending if success else False,
                'contract': contract, 'state_committed': False, 'hp_loss_resolved': success,
                'action_completed': False, 'action_phase_reply_available': False,
                'server_parity_verified': False, 'training_label_allowed': False,
                'settlement_allowed': False, 'winner_index': None}

    if effective_card_id != 0:
        return report(False, 'unsupported_effective_card')
    if packet['type'] != 0 or damage < 0 or packet['skip_wound_check'] or packet['hit_def'] or packet['feng_rui'] != 0:
        return report(False, 'unsupported_packet_shape')
    if (not isinstance(battle_context, Mapping) or battle_context.get('complete') is not True
            or battle_context.get('scene_behavior_present') is not False
            or battle_context.get('default_opponents') != [1, 0]
            or any(type(v) is not int for v in battle_context.get('default_opponents', []))):
        return report(False, 'missing_or_unsupported_battle_context')
    for i, player in enumerate(candidate):
        for key in ('max_hp', 'def'):
            _integer(player.get(key), key)
        if player['hp'] > player['max_hp']:
            return report(False, 'over_max_hp_state_out_of_scope:' + str(i))
        if player.get('card_config_overrides'):
            return report(False, 'dynamic_card_config_override:' + str(i))
        context = player.get('attack_context')
        if (not isinstance(context, Mapping) or context.get('complete') is not True
                or any(k not in context for k in CONTEXT_FIELDS)):
            return report(False, 'missing_complete_attack_context:' + str(i))
        for key in CONTEXT_FIELDS:
            if not isinstance(context[key], list):
                raise IncompleteCombatState('Explicit ID list required: ' + key)
            for value in context[key]:
                _integer(value, key, 1, 2**31-1)
            if context[key]:
                return report(False, 'unsupported_nonempty_' + key + ':' + str(i))
        resonance = player.get('resonance_context')
        if not isinstance(resonance, Mapping) or any(k not in resonance for k in ('selected_id', 'round', 'realm')):
            return report(False, 'missing_explicit_resonance_context:' + str(i))
        selected = _integer(resonance['selected_id'], 'resonance.selected_id')
        _integer(resonance['round'], 'resonance.round', 1)
        _integer(resonance['realm'], 'resonance.realm', 0, 6)
        if selected:
            return report(False, 'unsupported_resonance_selection:' + str(i))
        unsupported = set(player['raw_buffs']) - ALLOWED_BUFFS
        if unsupported:
            return report(False, 'unsupported_hit_buffs:' + str(i) + ':' + ','.join(sorted(unsupported, key=int)))

    def modify(index, key, delta):
        buffs = candidate[index]['raw_buffs']; before = buffs.get(key)
        if not delta or (before is None and delta < 0):
            return
        after = (before or 0) + delta
        _integer(after, 'candidate buff' + key, -1_000_000)
        if after > 0:
            buffs[key] = after
        else:
            buffs.pop(key, None)
        events.append({'player_index': index, 'event': 'modify_buff', 'buff_id': int(key),
                       'requested_delta': delta, 'before': before, 'after': buffs.get(key)})

    actor = candidate[src]['raw_buffs']; target = candidate[dst]['raw_buffs']
    bypass = '310' in actor or '4' in actor
    if '310' not in actor and '4' in actor:
        modify(src, '4', -1)
    hit_def = not bypass and candidate[dst]['def'] > 0
    if hit_def:
        old_def = candidate[dst]['def']; def_loss = min(damage, old_def)
        if damage > 0:
            candidate[dst]['def'] -= def_loss
            events.append({'player_index': dst, 'event': 'def_loss', 'amount': def_loss})
            modify(dst, '324', def_loss)
            # Native ModifyDef increments this unconditionally after a nonzero
            # change, even though its configured name suggests defense gain.
            modify(dst, '711', 1)
        damage = max(0, damage - old_def)
    if damage > 0 and '5' not in target:
        modify(src, '303', 1)
    final_packet.update(damage=damage, hit_def=hit_def)
    final_packet.pop('next_handler', None)
    final_packet.pop('not_hp_loss', None)
    huti_block = '5' in target and '433' not in actor
    if damage > 0:
        if '598' in target:
            hp_loss = 0
        elif huti_block:
            modify(dst, '5', -1); modify(dst, '745', -1)
        else:
            hp_loss = 1 if '677' in target else damage
            candidate[dst]['hp'] -= hp_loss
            _integer(candidate[dst]['hp'], 'candidate hp', -1_000_000)
            events.append({'player_index': dst, 'event': 'hp_loss', 'amount': hp_loss})
            modify(dst, '409', 1); modify(dst, '351', hp_loss)
        # OnHit branches on the packet, not its returned effective HP loss.
        if not huti_block and candidate[dst]['hp'] <= 0:
            revival_pending = can_revive(candidate[dst])
            if not revival_pending:
                guard_checked = True
                _check_one(candidate[dst], dst, events)
    if hp_loss > 0:
        modify(src, '302', hp_loss)
    return report(True)
