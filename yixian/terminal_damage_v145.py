"""Compare net destiny change separately from gross terminal damage.

This is a current-rule preview for explicit live players, never match mutation.
Postbattle recorded life is used only by the evaluator, not by this module.
"""
from pathlib import Path
from functools import lru_cache
import hashlib,json
from . import terminal_damage_v129 as previous
from .terminal_damage_v47 import _gains as validated_civet_gains

ROOT=Path(__file__).resolve().parents[1]
PROOF_SHA='fa61611721da09eb81f27b4b600b50de8a980995d11790f4ea83146ad1722fb9'
SURVIVAL_FATES={7,65,83,154}


@lru_cache(maxsize=1)
def extension_contract():
    raw=(ROOT/'data/inspection/combat-net-destiny-v145.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROOF_SHA:
        raise ValueError('combat_destiny_v145:proof_changed')
    facts=json.loads(raw)
    for name,expected in facts['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('combat_destiny_v145:source_changed:'+name)
    return facts


def unresolved(gross,reason):
    return {'resolved':False,'reason':reason,'gross_terminal_damage':gross,
            'predicted_net_destiny_change':None,'training_label_allowed':False}


def preview_net_destiny(compiled,result):
    facts=extension_contract()
    gross=previous.calculate_terminal_damage(compiled,result)
    if not gross.get('resolved'):
        return unresolved(gross,'gross_terminal_damage_unresolved')
    if any(p.get('is_mirror') is not False for p in compiled['effect_players']):
        return unresolved(gross,'authoritative_mirror_balance_unknown')
    if any(p.get('direct_destiny_lost')!=0 for p in result['players']):
        return unresolved(gross,'direct_destiny_interaction_unknown')
    receipt=result.get('combat_destiny_v145')
    if not isinstance(receipt,dict) or receipt.get('evidence_sha256')!=PROOF_SHA:
        return unresolved(gross,'explicit_native_destiny_receipt_required')
    if any(receipt.get(k) is not False for k in ['battle_bodies_changed','authoritative_match_state_mutated','training_label_allowed']):
        raise ValueError('combat_destiny_v145:read_only_receipt_required')
    before=[p['life'] for p in compiled['effect_players']]
    native_before=receipt.get('native_destiny_before');after=receipt.get('native_destiny_after')
    if (len(before)!=2 or native_before!=before or [p.get('destiny') for p in compiled['battle']['players']]!=before
        or not isinstance(after,list) or len(after)!=2 or any(type(x)is not int for x in before+after)):
        raise ValueError('combat_destiny_v145:invalid_native_balance')
    events=receipt.get('events');gains=[0,0];balances=list(before);chain_unknown=False
    cards={c['raw_id']:c for c in facts['cards']}
    if not isinstance(events,list):raise ValueError('combat_destiny_v145:events_required')
    for event in events:
        if not isinstance(event,dict):raise ValueError('combat_destiny_v145:invalid_event')
        seat=event.get('player_index');card=cards.get(event.get('raw_card'))
        if type(seat)is not int or seat not in (0,1) or type(event.get('raw_card'))is not int or card is None:
            raise ValueError('combat_destiny_v145:invalid_event_identity')
        lo,hi=event.get('native_destiny_before'),event.get('native_destiny_after')
        if (event.get('runtime_card')!=card['runtime_id'] or event.get('phase')!='card_body_after_hp_recovery'
            or event.get('authoritative_match_state_mutated') is not False
            or type(lo)is not int or type(hi)is not int
            or type(event.get('configured_gain'))is not int or type(event.get('observed_gain'))is not int
            or event.get('configured_gain')!=card['destiny_gain']
            or event.get('observed_gain')!=card['destiny_gain'] or hi-lo!=card['destiny_gain']):
            raise ValueError('combat_destiny_v145:invalid_jade_gain')
        chain_unknown |= lo!=balances[seat]
        balances[seat]=hi
        gains[seat]+=card['destiny_gain']
    if gains!=receipt.get('observed_jade_gains'):
        raise ValueError('combat_destiny_v145:gain_sum_mismatch')
    if chain_unknown or after!=balances or [a-b for a,b in zip(after,before)]!=gains:
        return unresolved(gross,'untracked_native_destiny_change')
    loser=gross['loser']
    # The existing Civet-specific user confirmation is not used to assert a
    # Jade/survival ordering that has not received its own evidence.
    if gains[loser] and set(compiled['effect_players'][loser]['fates'])&SURVIVAL_FATES:
        return unresolved(gross,'jade_survival_order_not_admitted')
    civet=validated_civet_gains(compiled,result['civet_v38']) if result.get('civet_v38') is not None else [0,0]
    total=[a+b for a,b in zip(gains,civet)]
    if any(b+g>2147483647 for b,g in zip(before,total)):
        return unresolved(gross,'destiny_exceeds_supported_int32')
    delta=list(total);delta[loser]-=gross['life_damage']
    return {'resolved':True,'gross_terminal_damage':gross,'jade_destiny_gains':gains,
            'civet_destiny_gains':civet,'combat_destiny_gains':total,
            'predicted_net_destiny_change':delta,'destiny_before':before,
            'predicted_destiny_after':[a+b for a,b in zip(before,delta)],
            'comparison_scope':'current_rule_preview_of_source_before_after_change',
            'source_game_version_certified':False,'match_state_mutated':False,
            'training_label_allowed':False}
