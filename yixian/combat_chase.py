"""Opt-in chase checkpoint with explicit scope and atomic unsupported branches.

Fixed card metadata describes eligibility only. It does not execute a card,
certify a legal deck, or supply missing choices from a replay. State and context
must come from the environment, never from a policy-supplied continuation flag.
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

EVIDENCE = 'data/inspection/combat-chase-v1.json'
EVIDENCE_HASH = 'c2c4067e7ee66b396fd0284c484f6dc41552af9c714a93904ce152f0790cb35d'
CONTEXT_FIELDS = ('fate_strategy_ids', 'xianmo_strategy_ids', 'talent_ids', 'keyin_type_ids')
SUPPORTED_DELTAS = {(15, -9), (15, -10), (272, -1), (413, -1),
                    (500, -1), (685, -1), (308, 1), (738, 1)}


def _integer(value, name, minimum=0, maximum=1_000_000):
    if type(value) is not int or not minimum <= value <= maximum:
        raise IncompleteCombatState('Explicit bounded integer required: '+name)
    return value


def _evidence(root=ROOT):
    raw=(Path(root)/EVIDENCE).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EVIDENCE_HASH:
        raise ValueError('Chase evidence hash mismatch')
    return json.loads(raw)


def load_chase_contract(root=ROOT):
    evidence=_evidence(root);boundaries=load_action_boundary_contract(root)
    if evidence['client_dll_sha256']!=boundaries['death_guard_contract']['client_dll_sha256']:
        raise ValueError('Chase and action boundary client versions differ')
    return {'schema_version':1,'scope':evidence['scope'],'evidence_sha256':EVIDENCE_HASH,
            'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'action_boundary_contract':boundaries,'game_mode_scope':3,
            'required_context_fields':list(CONTEXT_FIELDS),
            'effective_card_config_count':len(evidence['card_metadata']['known_card_ids']),
            'metadata_is_legality_or_effect_coverage':False,
            'implemented':'eligibility, prioritized costs,315 removal,308/738 counters and683 stop',
            'unresolved_policy':'commit neither player state nor tentative events',
            'unsupported':'104 without immunity and reached HP/def/anima/damage chase effects',
            'complete_chase_rules':False,'server_parity_verified':False,
            'full_action_scheduler_available':False,'training_label_allowed':False,
            'settlement_allowed':False}


def _modify(buffs, buff, delta, events, actor_index):
    """Only these signs/targets bypass all gameplay hooks in the pinned client."""
    if (buff,delta) not in SUPPORTED_DELTAS:
        raise IncompleteCombatState('Unsupported chase counter mutation')
    key=str(buff);before=buffs.get(key)
    if before is None and delta<0:
        return
    after=(before or 0)+delta
    _integer(after, 'buff_after:'+key, -1_000_000)
    if after<=0:
        buffs.pop(key,None)
    else:
        buffs[key]=after
    events.append({'player_index':actor_index,'buff_id':buff,'operation':'modify',
                   'requested_delta':delta,'before':before,'after':buffs.get(key)})


def resolve_chase(players, *, actor_index, effective_card_id, game_mode=3):
    """Resolve eligibility after the successful-card resurrection/death check.

chase_context.complete attests that all four ID lists were obtained completely
by the environment. An empty export or absent replay field is not that proof.
action_again_per_round is the current runtime limit, not an inferred default.
resonance_context uses the existing explicit selected_id/round/realm contract.
"""
    if type(game_mode) is not int or game_mode!=3:
        raise IncompleteCombatState('Only ordinary game mode3 is scoped')
    _integer(actor_index,'actor_index',0,1)
    _integer(effective_card_id,'effective_card_id',0,2**31-1)
    original=_players(players);states=deepcopy(original)
    actor=states[actor_index];opponent=states[1-actor_index]
    buffs=actor['raw_buffs'];other=opponent['raw_buffs']
    evidence=_evidence();meta=evidence['card_metadata'];contract=load_chase_contract()
    events=[];source=None

    def report(resolved, continue_action=None, reason=None):
        return {'resolved':resolved,'players':deepcopy(states if resolved else original),
                'events':deepcopy(events) if resolved else [],
                'continue_action':continue_action if resolved else None,
                'request_source':source,'stop_or_block_reason':reason,
                'effective_card_id':effective_card_id,'mutations_committed':resolved,
                'contract':contract,'complete_chase_rules':False,
                'server_parity_verified':False,'training_label_allowed':False,
                'settlement_allowed':False,'winner_index':None}

    if effective_card_id not in meta['known_card_ids']:
        return report(False,reason='unknown_effective_card_config')
    if actor.get('card_config_overrides'):
        return report(False,reason='dynamic_card_config_overrides_unsupported')
    context=actor.get('chase_context')
    if (not isinstance(context,Mapping) or context.get('complete') is not True
            or any(k not in context for k in CONTEXT_FIELDS)):
        return report(False,reason='missing_complete_chase_context')
    for key in CONTEXT_FIELDS:
        if not isinstance(context[key],list):
            raise IncompleteCombatState('Explicit complete ID list required: '+key)
        for value in context[key]:
            _integer(value,key,1,2**31-1)
    if 'action_again_per_round' not in actor:
        return report(False,reason='missing_runtime_chase_limit')
    limit=_integer(actor['action_again_per_round'],'action_again_per_round')
    fate=set(context['fate_strategy_ids']);season=set(context['xianmo_strategy_ids'])
    talents=set(context['talent_ids']);keyin=set(context['keyin_type_ids'])
    ignore=any(str(v) in buffs for v in (388,462,685)) or 28001 in season

    def remove315():
        if '315' in buffs:
            before=buffs.pop('315')
            events.append({'player_index':actor_index,'buff_id':315,
                           'operation':'remove','before':before,'after':None})

    if not ignore and any(str(v) in buffs for v in (215,561)):
        remove315()
        return report(True,False,'restriction215_or561')
    count=buffs.get('308',0)
    if effective_card_id in meta['action_again_card_ids']:
        source='card_action_again'
    else:
        source=next(('buff'+str(b) for b in (315,451,235) if str(b) in buffs),None)
    elements=meta['element_activation_buffs'].get(str(effective_card_id),[])
    if source is None and '272' in buffs and buffs.get('323',0)==0 and elements and count<limit:
        source='buff272';_modify(buffs,272,-1,events,actor_index)
    if source is None and '413' in buffs and count<limit and any(str(v) in buffs for v in elements):
        source='buff413';_modify(buffs,413,-1,events,actor_index)
    if source is None and '500' in buffs and effective_card_id in meta['subcategory8or9_card_ids'] and count<limit:
        source='buff500';_modify(buffs,500,-1,events,actor_index)
    cost=9 if 348 in fate or 7065 in season else 10
    if source is None and buffs.get('15',0)>=cost and count<limit:
        source='agility';_modify(buffs,15,-cost,events,actor_index)
    if source is None:
        return report(True,False,'no_chase_request')
    if '685' in buffs:
        _modify(buffs,685,-1,events,actor_index)
    remove315()
    if count>=limit:
        return report(True,False,'runtime_chase_limit')
    _modify(buffs,308,1,events,actor_index)
    if '104' in buffs and not ignore:
        return report(False,reason='unsupported_restriction104_effects')
    if '683' in buffs and not ignore:
        return report(True,False,'restriction683_after_counter')
    # Do not turn missing chase effects into an implicit no-op. Unresolved
    # later effects also roll back earlier costs/removals/counts atomically.
    if 340 in fate or 7112 in season:
        return report(False,reason='unsupported_chase_strategy_healing')
    if '235' in buffs:
        return report(False,reason='unsupported_chase_hp_cost235')
    if any(str(v) in other for v in (256,279)):
        return report(False,reason='unsupported_opponent_chase_effect')
    if 209 in talents and '444' in buffs:
        return report(False,reason='unsupported_talent209_chase_effect')
    if 163 in keyin:
        return report(False,reason='unsupported_keyin163_chase_effect')
    resonance=actor.get('resonance_context')
    if not isinstance(resonance,Mapping) or any(k not in resonance for k in ('selected_id','round','realm')):
        return report(False,reason='missing_explicit_resonance_context')
    selected=_integer(resonance['selected_id'],'resonance.selected_id',0,2**31-1)
    round_no=_integer(resonance['round'],'resonance.round',1)
    realm=_integer(resonance['realm'],'resonance.realm',0,6)
    r=evidence['resonance7']
    if selected==7 and round_no>=r['effectRound'] and realm>=r['effectLevel']:
        return report(False,reason='unsupported_effective_resonance7_chase_effect')
    if any(str(v) in buffs for v in (614,640,690)):
        return report(False,reason='unsupported_chase_buff_effect')
    _modify(buffs,738,1,events,actor_index)
    return report(True,True)


def advance_chase_checkpoint(state, *, effective_card_id):
    """Bind the environment result to the existing exact pending request."""
    request=pending_request(state)
    if request is None or request['phase']!='chase_resolution_and_effects':
        raise IncompleteCombatState('Pending chase checkpoint required')
    resolution=resolve_chase(request['players'],actor_index=request['actor_index'],
                             effective_card_id=effective_card_id)
    reply={'request_id':request['request_id'],'input_sha256':request['input_sha256'],
           'resolved':resolution['resolved'],'players':resolution['players'],
           'continue_action':resolution['continue_action']}
    return {'state':advance_actor_turn(state,reply),'chase':resolution,
            'request':request,'training_label_allowed':False,'settlement_allowed':False}
