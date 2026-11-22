"""Guarded client resurrection checkpoint; not a complete revival engine.

Only 430, 612 and 341 behavior is executable here. Other reached revival effects
block the whole transaction. The phase coordinator and existing adapter remain
unchanged; clients explicitly opt into this environment handler.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .combat_initialization import ROOT, IncompleteCombatState
from .combat_death_guard import _players
from .combat_action_boundaries import (
    load_action_boundary_contract, pending_request, advance_actor_turn,
)

EVIDENCE = 'data/inspection/combat-resurrection-v1.json'
EVIDENCE_HASH = 'deba0d1a7f3563428a2888d4d177db003c1230afbd85c27000a0e37ce89c86c2'
REVIVAL_ORDER = ('341', '231', '429', '597', '772')
UNSUPPORTED_EFFECTS = ('231', '429', '597', '772')
INT_MIN, INT_MAX = -(2**31), 2**31-1


def _integer(value, name, minimum=INT_MIN, maximum=INT_MAX):
    if type(value) is not int or not minimum <= value <= maximum:
        raise IncompleteCombatState('Explicit bounded integer required: '+name)
    return value


def load_resurrection_contract(root=ROOT):
    raw=(Path(root)/EVIDENCE).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EVIDENCE_HASH:
        raise ValueError('Resurrection evidence hash mismatch')
    evidence=json.loads(raw);boundaries=load_action_boundary_contract(root)
    if evidence['client_dll_sha256']!=boundaries['death_guard_contract']['client_dll_sha256']:
        raise ValueError('Resurrection and action boundary client versions differ')
    return {'schema_version':1,'scope':evidence['scope'],'evidence_sha256':EVIDENCE_HASH,
            'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'action_boundary_contract':boundaries,
            'talent139_hp':evidence['talent139']['otherParams'][1],
            'resonance48':{'bonus_hp':evidence['resonance48']['otherParams'][0],
                           'effect_round':evidence['resonance48']['effectRound'],
                           'effect_realm':evidence['resonance48']['effectLevel']},
            'implemented_effect_buffs':[430,612,341],
            'unsupported_reached_effect_buffs':[int(v) for v in UNSUPPORTED_EFFECTS],
            'pair_order':'active_actor_then_opponent_repeat_while_CanRevive',
            'missing_context_policy':'unresolved; commit no tentative mutations',
            'temporary_life_scope':'client_display_only_not_authoritative_settlement',
            'complete_resurrection_rules':False,'server_parity_verified':False,
            'full_action_scheduler_available':False,'training_label_allowed':False,
            'settlement_allowed':False}


def can_revive(player):
    """Exact scoped CanRevive predicate, not proof that effects are executable."""
    p=_players([player,player])[0]
    if p['hp']<=0 and '430' in p['raw_buffs']:
        return True
    if '612' in p['raw_buffs']:
        return False
    return p['hp']<=0 and any(b in p['raw_buffs'] for b in REVIVAL_ORDER)


def _resonance_bonus(player, contract):
    context=player.get('resonance_context')
    if not isinstance(context,Mapping) or any(k not in context for k in ('selected_id','round','realm')):
        return None
    selected=_integer(context['selected_id'],'resonance.selected_id',0)
    round_no=_integer(context['round'],'resonance.round',1)
    realm=_integer(context['realm'],'resonance.realm',0,6)
    meta=contract['resonance48']
    active=(selected==48 and round_no>=meta['effect_round'] and realm>=meta['effect_realm'])
    return meta['bonus_hp'] if active else 0


def resolve_resurrection(players, *, actor_index, game_mode=3, max_passes=16):
    """Resolve one checkpoint atomically, with immutable inputs and no labels.

    resonance_context is explicit environment state, never a policy choice.
    client_temp_life tracks only the client's temporary display value. This
    module does not debit persistent命元 or infer missing snapshot selections.
    """
    if type(game_mode) is not int or game_mode!=3:
        raise IncompleteCombatState('Only ordinary game mode3 is scoped')
    if type(actor_index) is not int or actor_index not in (0,1):
        raise IncompleteCombatState('Explicit active actor index required')
    _integer(max_passes,'max_passes',1,1024)
    original=_players(players); states=deepcopy(original)
    contract=load_resurrection_contract();events=[];order=[]

    def report(resolved, reason=None, blocked_index=None, passes=0):
        return {'resolved':resolved,'players':deepcopy(states if resolved else original),
                'events':deepcopy(events) if resolved else [],
                'visited_player_indices':list(order),'passes':passes,
                'blocked_reason':reason,'blocked_player_index':blocked_index,
                'mutations_committed':resolved,'contract':contract,
                'complete_resurrection_rules':False,'server_parity_verified':False,
                'training_label_allowed':False,'settlement_allowed':False,'winner_index':None}

    for pass_no in range(1,max_passes+1):
        for index in (actor_index,1-actor_index):
            order.append(index);p=states[index];buffs=p['raw_buffs']
            if p['hp']<=0 and '430' in buffs:
                if 'client_temp_life' not in p:
                    return report(False,'missing_client_temp_life_for430',index,pass_no)
                before=_integer(p['client_temp_life'],'client_temp_life')
                after=_integer(before-buffs['430'],'client_temp_life_after430')
                p['client_temp_life']=after;del buffs['430']
                events.append({'player_index':index,'effect_buff':430,
                               'client_temp_life_before':before,'client_temp_life_after':after,
                               'authoritative_life_settlement':False})
            if '612' in buffs:
                continue
            if p['hp']<=0 and '341' in buffs:
                bonus=_resonance_bonus(p,contract)
                if bonus is None:
                    return report(False,'missing_explicit_resonance_context_for341',index,pass_no)
                if 'max_hp' not in p:
                    return report(False,'missing_max_hp_for341',index,pass_no)
                old_max=_integer(p['max_hp'],'max_hp',0);old_hp=p['hp']
                target=_integer(contract['talent139_hp']+bonus,'resurrection_hp',1)
                p['max_hp']=target;p['hp']=target;del buffs['341']
                events.append({'player_index':index,'effect_buff':341,'hp_before':old_hp,
                               'hp_after':target,'max_hp_before':old_max,'max_hp_after':target,
                               'resonance48_bonus':bonus})
            if p['hp']<=0:
                unsupported=next((b for b in UNSUPPORTED_EFFECTS if b in buffs),None)
                if unsupported is not None:
                    return report(False,'unsupported_reached_resurrection_buff:'+unsupported,index,pass_no)
        if not any(can_revive(states[index]) for index in (actor_index,1-actor_index)):
            return report(True,passes=pass_no)
    return report(False,'resurrection_pass_limit',passes=max_passes)


def advance_resurrection_checkpoint(state):
    """Opt-in phase handler; returns the audit alongside the unchanged protocol."""
    request=pending_request(state)
    if request is None or not request['phase'].startswith('resurrection_'):
        raise IncompleteCombatState('Pending resurrection checkpoint required')
    resolution=resolve_resurrection(request['players'],actor_index=request['actor_index'])
    reply={'request_id':request['request_id'],'input_sha256':request['input_sha256'],
           'resolved':resolution['resolved'],'players':resolution['players']}
    return {'state':advance_actor_turn(state,reply),'resurrection':resolution,
            'request':request,'training_label_allowed':False,'settlement_allowed':False}
