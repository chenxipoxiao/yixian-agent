"""Single-actor boundary coordination with mandatory environment handlers.

This orders already-resolved effects. It implements neither card rules nor a
full battle scheduler, and never substitutes replay outcomes for missing hooks.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .combat_initialization import ROOT, IncompleteCombatState
from .combat_death_guard import (
    _players, check_death_boundary, cleanup_guard_at_turn_end,
    TURN_END_BOUNDARY, load_death_guard_contract,
)

EVIDENCE = 'data/inspection/action-boundaries-v1.json'
EVIDENCE_HASH = '22d8814e4d63b7af547df2b764037be7c7a327cc619547cf0dfbbc54372cd8ea'
PHASES = (
    'turn_start_effects', 'resurrection_after_turn_start', 'action_execution',
    'resurrection_after_successful_action', 'chase_resolution_and_effects',
    'resurrection_after_chase_effects', 'resurrection_before_turn_end',
    'turn_end_before_guard_cleanup', 'turn_end_after_guard_cleanup',
    'resurrection_after_turn_end',
)
FINISHED = ('client_stop', 'turn_completed', 'hook_limit_reached')


def _sha(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,
                                    separators=(',',':'),allow_nan=False).encode()).hexdigest()


def load_action_boundary_contract(root=ROOT):
    raw=(Path(root)/EVIDENCE).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EVIDENCE_HASH:
        raise ValueError('Action boundary evidence hash mismatch')
    evidence=json.loads(raw);guard=load_death_guard_contract(root)
    if evidence['death_guard_evidence_sha256']!=guard['evidence_sha256']:
        raise ValueError('Action boundary and guard evidence differ')
    return {'schema_version':1,'scope':evidence['scope'],'evidence_sha256':EVIDENCE_HASH,
            'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'death_guard_contract':guard,'required_handlers':list(PHASES),
            'game_mode_scope':3,'supported_action_result':1,
            'missing_handler_policy':'wait; no implicit no-op or result inference',
            'phase_reply_origin':'environment execution only, never a policy action or inferred replay trace',
            'full_action_scheduler_available':False,'card_effects_implemented':False,
            'resurrection_rules_implemented':False,'server_parity_verified':False,
            'training_label_allowed':False,'settlement_allowed':False}


def begin_actor_turn(players, *, actor_index, sequence_id, max_completed_hooks=128, game_mode=3):
    if type(game_mode)is not int or game_mode!=3:
        raise IncompleteCombatState('Only ordinary mode3 boundary coordination is scoped')
    if type(actor_index)is not int or actor_index not in (0,1):
        raise IncompleteCombatState('Explicit actor index required; slots retain left/right order')
    if not isinstance(sequence_id,str) or not sequence_id or len(sequence_id)>128:
        raise IncompleteCombatState('Nonempty bounded environment sequence ID required')
    if type(max_completed_hooks)is not int or not 1<=max_completed_hooks<=1024:
        raise IncompleteCombatState('Finite hook budget required')
    return {'schema_version':1,'sequence_id':sequence_id,'actor_index':actor_index,
            'players':_players(players),'phase':'turn_start_effects','completed_hooks':0,
            'max_completed_hooks':max_completed_hooks,'trace':[],
            'contract_sha256':_sha(load_action_boundary_contract()),
            'status':'waiting_for_environment_handler','blocked_reason':None,
            'full_action_scheduler_available':False,'training_label_allowed':False,
            'settlement_allowed':False,'winner_index':None}


def _validate(state):
    if (not isinstance(state,Mapping) or type(state.get('schema_version'))is not int or state.get('schema_version')!=1
            or state.get('contract_sha256')!=_sha(load_action_boundary_contract())):
        raise IncompleteCombatState('Boundary state contract mismatch')
    if state.get('phase') not in PHASES+FINISHED:
        raise IncompleteCombatState('Unknown boundary phase')
    if type(state.get('actor_index'))is not int or state['actor_index'] not in (0,1):
        raise IncompleteCombatState('Invalid boundary actor')
    if (not isinstance(state.get('sequence_id'),str) or not 1<=len(state['sequence_id'])<=128
            or not isinstance(state.get('trace'),list)):
        raise IncompleteCombatState('Invalid boundary identity or trace')
    if (type(state.get('completed_hooks'))is not int or type(state.get('max_completed_hooks'))is not int
            or not 0<=state['completed_hooks']<=state['max_completed_hooks']<=1024
            or state['max_completed_hooks']<1 or len(state.get('trace',[]))!=state['completed_hooks']):
        raise IncompleteCombatState('Invalid hook progress')
    if (state['phase'] not in FINISHED and state['completed_hooks']>=state['max_completed_hooks']
            or any(state.get(k)is not False for k in ('training_label_allowed','settlement_allowed','full_action_scheduler_available'))
            or state.get('winner_index')is not None):
        raise IncompleteCombatState('Boundary limit or label guard violated')
    _players(state['players'])


def pending_request(state):
    _validate(state)
    if state['phase'] in FINISHED:
        return None
    body={'request_id':f"{state['sequence_id']}:{state['completed_hooks']}",
          'phase':state['phase'],'actor_index':state['actor_index'],
          'players':deepcopy(state['players']),'contract_sha256':state['contract_sha256']}
    return dict(body,input_sha256=_sha(body))


def advance_actor_turn(state, reply=None):
    """Accept one exact environment reply, then apply only this boundary's logic.

    A resolved reply attests that its named effects were executed by an external
    environment handler; this coordinator does not certify that handler. Tests
    may supply explicitly synthetic replies, which must never become training.
    """
    request=pending_request(state)
    if request is None:
        raise IncompleteCombatState('No pending handler; completed/limited states cannot advance')
    result=deepcopy(dict(state));phase=request['phase']
    if reply is None:
        result['blocked_reason']='required_environment_handler_unavailable'
        return result
    if (not isinstance(reply,Mapping) or reply.get('request_id')!=request['request_id']
            or reply.get('input_sha256')!=request['input_sha256'] or type(reply.get('resolved'))is not bool):
        raise IncompleteCombatState('Missing, stale, or malformed phase reply')
    if not reply['resolved']:
        result['blocked_reason']='environment_handler_unresolved'
        return result
    if phase=='action_execution' and (type(reply.get('action_result'))is not int or reply['action_result']!=1):
        raise IncompleteCombatState('Non-successful action branches remain unsupported')
    if phase=='chase_resolution_and_effects' and type(reply.get('continue_action'))is not bool:
        raise IncompleteCombatState('Explicit environment chase decision required')
    states=_players(reply.get('players'))
    event={'phase':phase,'request_id':request['request_id'],'input_sha256':request['input_sha256'],
           'guard_events':[]}
    if phase.startswith('resurrection_'):
        checked=check_death_boundary(states)
        states=checked['players'];event['guard_events']=checked['events']
        event['candidate_death_check']=checked['candidate_death_check']
        event['checked_player_indices']=checked['checked_player_indices']
        if phase in ('resurrection_after_successful_action','resurrection_after_chase_effects'):
            next_phase='resurrection_before_turn_end' if checked['candidate_death_check'] else (
                'chase_resolution_and_effects' if phase=='resurrection_after_successful_action' else 'action_execution')
        elif checked['candidate_death_check']:
            next_phase='client_stop'
        else:
            next_phase={'resurrection_after_turn_start':'action_execution',
                        'resurrection_before_turn_end':'turn_end_before_guard_cleanup',
                        'resurrection_after_turn_end':'turn_completed'}[phase]
    elif phase=='turn_end_before_guard_cleanup':
        cleaned=cleanup_guard_at_turn_end(states,actor_index=state['actor_index'],boundary=TURN_END_BOUNDARY)
        states=cleaned['players'];event['guard_events']=cleaned['events']
        next_phase='turn_end_after_guard_cleanup'
    elif phase=='chase_resolution_and_effects':
        event['environment_continue_action']=reply['continue_action']
        next_phase='resurrection_after_chase_effects' if reply['continue_action'] else 'resurrection_before_turn_end'
    else:
        next_phase={'turn_start_effects':'resurrection_after_turn_start',
                    'action_execution':'resurrection_after_successful_action',
                    'turn_end_after_guard_cleanup':'resurrection_after_turn_end'}[phase]
    result['completed_hooks']+=1;result['trace'].append(event);result['players']=states
    if next_phase not in FINISHED and result['completed_hooks']>=result['max_completed_hooks']:
        next_phase='hook_limit_reached'
    result.update(phase=next_phase,blocked_reason=None,
                  status='waiting_for_environment_handler' if next_phase not in FINISHED else next_phase,
                  full_action_scheduler_available=False,training_label_allowed=False,
                  settlement_allowed=False,winner_index=None)
    return result
