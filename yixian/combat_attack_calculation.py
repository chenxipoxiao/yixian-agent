"""Guarded normal-attack calculation prefix, ending before ApplyDamage.

The candidate counters and packet are a proposed transaction, never a completed
card or HP loss. Missing context and unsupported content block the calculation;
the original input is never mutated and no phase reply is produced.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .combat_initialization import ROOT, IncompleteCombatState
from .combat_death_guard import _players
from .combat_action_boundaries import load_action_boundary_contract

EVIDENCE='data/inspection/combat-attack-calculation-v1.json'
EVIDENCE_HASH='d79b01e1451316f10fdde964444eb19a82b36d4805dc4fa45362512a86513158'
CONTEXT_FIELDS=('fate_strategy_ids','xianmo_strategy_ids','talent_ids','keyin_type_ids')
# These keys are either handled here or inert within this precise prefix.
# This is NOT a declaration about their behavior in ApplyDamage or OnHit.
ALLOWED_BUFFS=frozenset(map(str,(2,6,9,12,101,102,103,212,322,440,
    306,323,333,493,326,17,18,15,308,738,315,451,215,561,388,462,685,683)))
INT_MIN,INT_MAX=-(2**31),2**31-1


def _integer(value,name,minimum=0,maximum=INT_MAX):
    if type(value) is not int or not minimum<=value<=maximum:
        raise IncompleteCombatState('Explicit bounded integer required: '+name)
    return value


def _evidence(root=ROOT):
    data=(Path(root)/EVIDENCE).read_bytes()
    if hashlib.sha256(data).hexdigest()!=EVIDENCE_HASH:
        raise ValueError('Attack calculation evidence hash mismatch')
    return json.loads(data)


def load_attack_calculation_contract(root=ROOT):
    evidence=_evidence(root);boundary=load_action_boundary_contract(root)
    if evidence['client_dll_sha256']!=boundary['death_guard_contract']['client_dll_sha256']:
        raise ValueError('Attack calculation and action boundary client versions differ')
    return {'schema_version':1,'scope':evidence['scope'],'evidence_sha256':EVIDENCE_HASH,
            'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'action_boundary_contract':boundary,'game_mode_scope':3,
            'effective_card_id':0,'base_attack':evidence['normal_card']['attack'],
            'allowed_prefix_buff_ids':sorted(map(int,ALLOWED_BUFFS)),
            'context_policy':'explicit complete empty ID lists and resonance0 on both players',
            'transaction_policy':'candidate states only; no ApplyDamage, HP mutation, or action reply',
            'full_attack_execution_available':False,'complete_card_execution_available':False,
            'server_parity_verified':False,'training_label_allowed':False,'settlement_allowed':False}


def prepare_normal_attack(players, *, actor_index, effective_card_id, next_card_id, game_mode=3):
    """Prepare the exact supported CalculateAttack prefix for effective card0.

The caller must resolve the *actual* next card, not use a placeholder zero.
attack_context.complete is an environment attestation of complete fields;
absent replay selections are unknown, never empty lists. Even a successful
preparation still requires a future ApplyDamage transaction and card hooks.
"""
    if type(game_mode) is not int or game_mode!=3:
        raise IncompleteCombatState('Only ordinary mode3 is scoped')
    _integer(actor_index,'actor_index',0,1)
    _integer(effective_card_id,'effective_card_id')
    _integer(next_card_id,'next_card_id')
    original=_players(players);candidate=deepcopy(original)
    contract=load_attack_calculation_contract();evidence=_evidence();events=[]
    body={'players':original,'actor_index':actor_index,'effective_card_id':effective_card_id,
          'next_card_id':next_card_id,'contract':contract}
    input_hash=hashlib.sha256(json.dumps(body,ensure_ascii=False,sort_keys=True,
                                       separators=(',',':'),allow_nan=False).encode()).hexdigest()

    def report(prepared, reason=None, packet=None, arithmetic=None):
        return {'calculation_prepared':prepared,'blocked_reason':reason,
                'input_sha256':input_hash,
                'candidate_players':deepcopy(candidate if prepared else original),
                'candidate_events':deepcopy(events) if prepared else [],
                'pending_damage_packet':deepcopy(packet) if prepared else None,
                'arithmetic':deepcopy(arithmetic) if prepared else None,'contract':contract,
                'state_committed':False,'hp_loss_resolved':False,
                'action_completed':False,'action_phase_reply_available':False,
                'server_parity_verified':False,'training_label_allowed':False,
                'settlement_allowed':False,'winner_index':None}

    if effective_card_id!=0:
        return report(False,'unsupported_effective_card')
    if next_card_id not in evidence['known_next_card_ids']:
        return report(False,'unknown_next_card_config')
    if next_card_id in evidence['unsupported_adjacent_card_ids']:
        return report(False,'unsupported_adjacent_card_effect')
    for index,p in enumerate(candidate):
        if p.get('card_config_overrides'):
            return report(False,'dynamic_card_config_override:'+str(index))
        context=p.get('attack_context')
        if (not isinstance(context,Mapping) or context.get('complete') is not True
                or any(k not in context for k in CONTEXT_FIELDS)):
            return report(False,'missing_complete_attack_context:'+str(index))
        for key in CONTEXT_FIELDS:
            ids=context[key]
            if not isinstance(ids,list):
                raise IncompleteCombatState('Explicit ID list required: '+key)
            for value in ids:_integer(value,key,1)
            if ids:return report(False,'unsupported_nonempty_'+key+':'+str(index))
        resonance=p.get('resonance_context')
        if not isinstance(resonance,Mapping) or any(k not in resonance for k in ('selected_id','round','realm')):
            return report(False,'missing_explicit_resonance_context:'+str(index))
        selected=_integer(resonance['selected_id'],'resonance.selected_id')
        _integer(resonance['round'],'resonance.round',1)
        _integer(resonance['realm'],'resonance.realm',0,6)
        if selected!=0:return report(False,'unsupported_resonance_selection:'+str(index))
        unsupported=set(p['raw_buffs'])-ALLOWED_BUFFS
        if unsupported:return report(False,'unsupported_prefix_buffs:'+str(index)+':'+','.join(sorted(unsupported,key=int)))
    actor=candidate[actor_index]['raw_buffs'];target=candidate[1-actor_index]['raw_buffs']

    def set_buff(index,key,value,operation):
        buffs=candidate[index]['raw_buffs'];before=buffs.get(key)
        if abs(value)>1_000_000:
            raise IncompleteCombatState('Candidate counter outside supported state bounds: '+key)
        if value>0:buffs[key]=value
        else:buffs.pop(key,None)
        events.append({'player_index':index,'buff_id':int(key),'operation':operation,
                       'before':before,'after':buffs.get(key)})

    for key in ('323','333','493'):
        set_buff(actor_index,key,actor.get(key,0)+1,'modify+1')
    set_buff(1-actor_index,'326',target.get('326',0)+1,'modify+1')
    attack=evidence['normal_card']['attack']
    if '6' in actor:
        attack+=actor['6'];set_buff(actor_index,'306',actor['6'],'set_sword_intent_used')
    attack+=actor.get('212',0)
    attack+=actor.get('2',0)
    additive=attack
    if '103' in actor and attack>1:
        attack=max(1,attack-actor['103'])
    after_reduction=attack
    if '9' in target:
        attack=max(1,attack-evidence['iron_bone_card']['otherParams'][0])
    after_iron=attack
    percent=100
    if '102' in target:percent+=target.get('440',40)
    if '101' in actor and '322' not in actor:percent-=actor.get('440',40)
    if '12' in target:percent-=40
    percent=max(0,percent)
    # In this subset every rate is an integer percent. Round(rate*100) in
    # the client therefore yields this integer. Retain integer truncation;
    # multiplication that would overflow client int32 is deliberately blocked.
    if attack>0:
        product=percent*attack
        if not INT_MIN<=product<=INT_MAX:
            return report(False,'int32_product_overflow_out_of_scope')
        attack=max(1,product//100)
    packet={'source_index':actor_index,'target_index':1-actor_index,'type':0,
            'damage':attack,'skip_wound_check':False,'hit_def':False,'feng_rui':0,
            'next_handler':'ApplyDamage','not_hp_loss':True}
    arithmetic={'base_attack':evidence['normal_card']['attack'],'after_additive':additive,
                'after_reduction103':after_reduction,'after_iron_bone9':after_iron,
                'combined_percent':percent,'calculated_attack':attack}
    return report(True,packet=packet,arithmetic=arithmetic)
