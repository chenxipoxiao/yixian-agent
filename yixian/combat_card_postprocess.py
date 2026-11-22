"""Versioned card0 post-effect bookkeeping and cleanup candidate.

Starts after the earlier OnAfterExecuted triggers, NOT after just a hit.
Those triggers and OnBeforeExecuted remain the caller's responsibility.
The older cleanup-only interface and its frozen contract are unchanged.
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
from .combat_card_cleanup import ALLOWED_BUFFS as CLEANUP_BUFFS, load_card_cleanup_contract

EVIDENCE = 'data/inspection/card-postprocess-v1.json'
EVIDENCE_HASH = 'b5196726c35e6c54c967f595072b8a382025838fdf471ca009751216bc217a38'
BOUNDARY = 'on_after_executed_after_trigger_effects_before_bookkeeping'
ALLOWED_BUFFS = CLEANUP_BUFFS | frozenset(map(str, (
    304, 305, 337, 338, 357, 492, 504, 331, 546, 571, 624, 662, 395, 720)))


def load_card_postprocess_contract(root=ROOT):
    raw = (Path(root)/EVIDENCE).read_bytes()
    if hashlib.sha256(raw).hexdigest() != EVIDENCE_HASH:
        raise ValueError('Card postprocess evidence hash mismatch')
    evidence = json.loads(raw)
    prior = load_card_cleanup_contract(root)
    if evidence['client_dll_sha256'] != prior['client_dll_sha256']:
        raise ValueError('Card postprocess and cleanup client versions differ')
    return {'schema_version': 1, 'scope': evidence['scope'],
            'evidence_sha256': EVIDENCE_HASH,
            'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'client_dll_sha256': evidence['client_dll_sha256'],
            'prior_cleanup_contract': prior, 'boundary': BOUNDARY,
            'effective_card_id': 0, 'game_mode_scope': 3,
            'allowed_postprocess_buff_ids': sorted(map(int, ALLOWED_BUFFS)),
            'context_policy': 'explicit complete empty selections and resonance0; explicit earlier-trigger boundary',
            'candidate_transaction_only': True, 'whole_post_card_hook_completed': False,
            'action_phase_reply_available': False, 'server_parity_verified': False,
            'training_label_allowed': False, 'settlement_allowed': False}


def resolve_normal_card_postprocess(players, *, actor_index, card_item,
                                    is_temp_card, checkpoint, game_mode=3):
    """Resolve the pinned post-effect suffix including category bookkeeping.

    Card0's classification can change due to combat markers; its printed name
    alone does not establish whether it extends a cloud-sword chain. Missing
    selection context never means empty selections. No input is mutated.
    """
    if type(game_mode) is not int or game_mode != 3:
        raise IncompleteCombatState('Only ordinary mode3 is scoped')
    _integer(actor_index, 'actor_index', 0, 1)
    if type(is_temp_card) is not bool:
        raise IncompleteCombatState('Explicit is_temp_card boolean required')
    if not isinstance(card_item, Mapping):
        raise IncompleteCombatState('Explicit card item required')
    _integer(card_item.get('effective_card_id'), 'card_item.effective_card_id')
    if type(card_item.get('had_used')) is not bool:
        raise IncompleteCombatState('Explicit card_item.had_used boolean required')
    original = _players(players)
    original_item = deepcopy(dict(card_item))
    candidate = deepcopy(original); item = deepcopy(original_item); events = []
    classification = None
    contract = load_card_postprocess_contract()
    body = {'players': original, 'actor_index': actor_index, 'card_item': original_item,
            'is_temp_card': is_temp_card, 'checkpoint': checkpoint,
            'game_mode': game_mode, 'contract': contract}
    input_hash = hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True,
                                          separators=(',', ':'), allow_nan=False).encode()).hexdigest()

    def report(resolved, reason=None):
        return {'postprocess_resolved': resolved, 'blocked_reason': reason,
                'input_sha256': input_hash, 'contract': contract,
                'candidate_players': deepcopy(candidate if resolved else original),
                'candidate_card_item': deepcopy(item if resolved else original_item),
                'candidate_events': deepcopy(events) if resolved else [],
                'classification': deepcopy(classification) if resolved else None,
                'state_committed': False, 'earlier_triggers_verified_by_this_component': False,
                'whole_post_card_hook_completed': False, 'action_completed': False,
                'action_phase_reply_available': False, 'server_parity_verified': False,
                'training_label_allowed': False, 'settlement_allowed': False, 'winner_index': None}

    if (not isinstance(checkpoint, Mapping) or checkpoint.get('boundary') != BOUNDARY
            or checkpoint.get('earlier_triggers_resolved') is not True):
        return report(False, 'missing_explicit_postprocess_boundary')
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
            return report(False, 'unsupported_postprocess_buffs:'+str(index)+':'+','.join(sorted(unknown, key=int)))

    buffs = candidate[actor_index]['raw_buffs']

    def remove(key):
        if key in buffs:
            before = buffs.pop(key)
            events.append({'player_index': actor_index, 'buff_id': int(key),
                           'operation': 'remove', 'before': before, 'after': None})

    def modify(key, delta):
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
        # Native ModifyBuffValue includes this secondary counter even when
        # 304 was raised by chain preservation rather than IsYunJian itself.
        if key == '304' and delta > 0:
            modify('720', delta)

    remove('337'); remove('333')
    qualifies492 = '492' in buffs and buffs.get('504', 0) <= buffs['492']
    qualifies331 = '331' in buffs and buffs.get('546', 0) <= buffs['331']
    kuang = ('338' in buffs and '357' in buffs) or qualifies492 or qualifies331
    yun = '338' in buffs or ('357' in buffs and kuang) or qualifies492 or '571' in buffs
    classification = {'is_yun_jian': yun, 'is_kuang_jian': kuang,
                      'is_jian': False, 'is_ling_jian': False, 'is_jian_zhen': False,
                      'evaluated_before_charge_decrement': True}
    if yun:
        modify('304', 1)
    elif '624' in buffs:
        modify('304', 1)
        modify('624', -1)
    else:
        remove('304')
    if kuang:
        modify('305', 1)
    # Card0 is hidden, career/subcategory/cardType0, has no HP cost and no
    # matching name/description tokens. All other category increments skip.
    for charge, counter in (('492', '504'), ('331', '546')):
        if charge in buffs:
            count = buffs.get(counter, 0)
            if 0 < count <= buffs[charge]:
                modify(charge, -1)
            modify(counter, -1)
    if not is_temp_card:
        remove('662')
    remove('395')

    # Same pinned cleanup semantics as the prior version, executed on the
    # complete candidate state. New category markers are never filtered out.
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
    remove('330')
    modify('363', 1)
    remove('382')
    return report(True)
