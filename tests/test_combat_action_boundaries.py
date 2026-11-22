from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from yixian.combat_initialization import ROOT, IncompleteCombatState
from yixian.combat_action_boundaries import (
    EVIDENCE, begin_actor_turn, pending_request, advance_actor_turn,
    load_action_boundary_contract,
)


def player(hp=10,buffs=None):
    return {'hp':hp,'raw_buffs':{} if buffs is None else buffs}


def turn(players=None,actor=0,budget=128,identity='explicit-test-fixture'):
    return begin_actor_turn([player(),player()] if players is None else players,
                            actor_index=actor,sequence_id=identity,max_completed_hooks=budget)


def resolved(state,players=None,**extra):
    # Explicit synthetic environment reply, never a reconstructed replay action.
    r=pending_request(state)
    return dict(request_id=r['request_id'],input_sha256=r['input_sha256'],resolved=True,
                players=deepcopy(r['players'] if players is None else players),**extra)


def step(state,players=None,**extra):
    return advance_actor_turn(state,resolved(state,players,**extra))


class ActionBoundaryTests(unittest.TestCase):
    def test_start_effects_must_precede_resurrection_and_death(self):
        s=turn([player(0,{'17':1}),player()])
        self.assertEqual(s['phase'],'turn_start_effects');self.assertIn('17',s['players'][0]['raw_buffs'])
        s=step(s);self.assertEqual(s['phase'],'resurrection_after_turn_start')
        self.assertIn('17',s['players'][0]['raw_buffs'])
        s=step(s);self.assertEqual(s['phase'],'action_execution');self.assertEqual(s['players'][0]['raw_buffs'],{'18':1})

    def test_resurrection_before_check_can_save17_from_consumption(self):
        s=step(turn([player(0,{'17':1}),player()]))
        saved=deepcopy(s['players']);saved[0]['hp']=2;s=step(s,saved)
        self.assertEqual(s['phase'],'action_execution');self.assertEqual(s['players'][0]['raw_buffs'],{'17':1})

    def test_no_handler_does_not_run_death_check_or_consume_guard(self):
        s=step(turn([player(0,{'17':1}),player()]))
        blocked=advance_actor_turn(s)
        self.assertEqual(blocked['players'],s['players']);self.assertEqual(blocked['completed_hooks'],1)
        self.assertEqual(blocked['phase'],'resurrection_after_turn_start')

    def test_unresolved_reply_discards_partial_state(self):
        s=turn();reply=resolved(s,[player(-10),player()]);reply['resolved']=False
        blocked=advance_actor_turn(s,reply)
        self.assertEqual(blocked['players'],s['players']);self.assertEqual(blocked['completed_hooks'],0)

    def test_turn_start_stop_never_executes_card_or_selects_winner(self):
        s=step(step(turn([player(0),player()])))
        self.assertEqual(s['phase'],'client_stop');self.assertIsNone(pending_request(s));self.assertIsNone(s['winner_index'])
        with self.assertRaises(IncompleteCombatState):advance_actor_turn(s)

    def test_successful_action_requires_its_own_resurrection_checkpoint(self):
        s=step(step(turn()));s=step(s,[player(-1,{'17':1}),player()],action_result=1)
        self.assertEqual(s['phase'],'resurrection_after_successful_action')
        self.assertEqual(s['players'][0]['raw_buffs'],{'17':1})
        s=step(s);self.assertEqual(s['phase'],'chase_resolution_and_effects')
        self.assertEqual(s['players'][0]['raw_buffs'],{'18':1})

    def test_post_action_positive_death_check_routes_to_shared_pre_end(self):
        s=step(step(turn()));s=step(s,[player(0),player()],action_result=1);s=step(s)
        self.assertEqual(s['phase'],'resurrection_before_turn_end')
        self.assertIsNotNone(pending_request(s));self.assertFalse(s['settlement_allowed'])

    def test_shared_pre_end_resurrection_can_avoid_stop_after_card(self):
        s=step(step(turn()));s=step(s,[player(0),player()],action_result=1);s=step(s)
        s=step(s,[player(2),player()]);self.assertEqual(s['phase'],'turn_end_before_guard_cleanup')

    def test_chase_retains18_until_owner_turn_end(self):
        s=step(step(turn([player(1,{'17':1}),player()])))
        s=step(s,[player(-1,{'17':1}),player()],action_result=1);s=step(s)
        s=step(s,continue_action=True);self.assertEqual(s['phase'],'resurrection_after_chase_effects')
        self.assertIn('18',s['players'][0]['raw_buffs'])
        s=step(s);self.assertEqual(s['phase'],'action_execution');self.assertIn('18',s['players'][0]['raw_buffs'])
        s=step(s,action_result=1);s=step(s);s=step(s,continue_action=False);s=step(s)
        self.assertEqual(s['phase'],'turn_end_before_guard_cleanup');self.assertIn('18',s['players'][0]['raw_buffs'])
        s=step(s);self.assertEqual(s['phase'],'turn_end_after_guard_cleanup');self.assertNotIn('18',s['players'][0]['raw_buffs'])
        s=step(s);self.assertEqual(s['phase'],'resurrection_after_turn_end')
        s=step(s);self.assertEqual(s['phase'],'client_stop')

    def test_chase_effect_death_check_routes_to_pre_end(self):
        s=step(step(turn()));s=step(s,action_result=1);s=step(s)
        s=step(s,[player(-1),player()],continue_action=True)
        s=step(s);self.assertEqual(s['phase'],'resurrection_before_turn_end')

    def test_remaining_turn_end_effects_run_after_cleanup_before_check(self):
        s=step(step(turn([player(1,{'18':1}),player()])))
        s=step(s,action_result=1);s=step(s);s=step(s,continue_action=False);s=step(s)
        s=step(s);self.assertNotIn('18',s['players'][0]['raw_buffs'])
        s=step(s,[player(0),player()]);self.assertEqual(s['phase'],'resurrection_after_turn_end')
        s=step(s,[player(2),player()]);self.assertEqual(s['phase'],'turn_completed')

    def test_cleanup_uses_actor_not_left_slot(self):
        s=step(step(turn([player(2,{'18':1}),player(2,{'18':1})],actor=1)))
        s=step(s,action_result=1);s=step(s);s=step(s,continue_action=False);s=step(s);s=step(s)
        self.assertIn('18',s['players'][0]['raw_buffs']);self.assertNotIn('18',s['players'][1]['raw_buffs'])

    def test_death_check_retains_left_right_short_circuit_order(self):
        s=step(turn([player(-2,{'17':1}),player(-1,{'17':1})],actor=1));s=step(s)
        self.assertEqual(s['trace'][-1]['checked_player_indices'],[0])
        self.assertIn('17',s['players'][1]['raw_buffs'])

    def test_missing_turn_end_handler_does_not_clear18(self):
        s=step(step(turn([player(1,{'18':1}),player()])))
        s=step(s,action_result=1);s=step(s);s=step(s,continue_action=False);s=step(s)
        blocked=advance_actor_turn(s);self.assertIn('18',blocked['players'][0]['raw_buffs'])

    def test_invalid_action_status_fails_without_applying_reply(self):
        s=step(step(turn()));old=deepcopy(s)
        for result in (None,0,2,True,'1'):
            with self.subTest(result=result),self.assertRaises(IncompleteCombatState):step(s,[player(0),player()],action_result=result)
        self.assertEqual(s,old)

    def test_chase_decision_must_be_explicit_environment_boolean(self):
        s=step(step(turn()));s=step(s,action_result=1);s=step(s)
        for decision in (None,1,'false'):
            with self.subTest(decision=decision),self.assertRaises(IncompleteCombatState):step(s,continue_action=decision)

    def test_stale_duplicate_and_foreign_replies_rejected(self):
        s=turn();reply=resolved(s);next_state=advance_actor_turn(s,reply)
        with self.assertRaises(IncompleteCombatState):advance_actor_turn(next_state,reply)
        foreign=turn(identity='different-fixture')
        with self.assertRaises(IncompleteCombatState):advance_actor_turn(foreign,reply)
        reply['input_sha256']='bad'
        with self.assertRaises(IncompleteCombatState):advance_actor_turn(s,reply)

    def test_changed_state_invalidates_pending_reply(self):
        s=turn();reply=resolved(s);s['players'][0]['hp']=2
        with self.assertRaises(IncompleteCombatState):advance_actor_turn(s,reply)

    def test_missing_players_or_wrong_resolved_type_rejects(self):
        s=turn();reply=resolved(s);del reply['players']
        with self.assertRaises(IncompleteCombatState):advance_actor_turn(s,reply)
        reply=resolved(s);reply['resolved']='true'
        with self.assertRaises(IncompleteCombatState):advance_actor_turn(s,reply)

    def test_hook_limit_never_becomes_win_loss(self):
        s=step(turn(budget=1));self.assertEqual(s['phase'],'hook_limit_reached')
        self.assertFalse(s['training_label_allowed']);self.assertFalse(s['settlement_allowed']);self.assertIsNone(s['winner_index'])
        self.assertIsNone(pending_request(s))

    def test_unresolved_retry_does_not_spend_budget_or_change_request(self):
        s=turn(budget=1);request=pending_request(s)
        for _ in range(3):s=advance_actor_turn(s)
        self.assertEqual(pending_request(s),request);self.assertEqual(s['completed_hooks'],0)

    def test_caller_cannot_promote_label_or_scheduler_flags(self):
        for key in ('training_label_allowed','settlement_allowed','full_action_scheduler_available'):
            s=turn();s[key]=True
            with self.subTest(key=key),self.assertRaises(IncompleteCombatState):pending_request(s)

    def test_inputs_and_requested_copies_are_independent(self):
        players=[player(),player()];old=deepcopy(players);s=turn(players);request=pending_request(s)
        request['players'][0]['hp']=-1
        self.assertEqual(s['players'],old);self.assertEqual(players,old)
        previous=deepcopy(s);step(s);self.assertEqual(s,previous)

    def test_invalid_initial_scope_actor_identity_and_budget(self):
        for values in ({'actor_index':True,'sequence_id':'x'},{'actor_index':0,'sequence_id':''},
                       {'actor_index':0,'sequence_id':'x','game_mode':16},
                       {'actor_index':0,'sequence_id':'x','max_completed_hooks':0}):
            with self.subTest(values=values),self.assertRaises(IncompleteCombatState):begin_actor_turn([player(),player()],**values)

    def test_invalid_phase_contract_and_trace_reject(self):
        for key,value in [('phase','arbitrary'),('contract_sha256','bad'),('trace',None),('actor_index',2),('schema_version',True)]:
            s=turn();s[key]=value
            with self.subTest(key=key),self.assertRaises(IncompleteCombatState):pending_request(s)

    def test_contract_pin_and_unsupported_full_battle_claims(self):
        c=load_action_boundary_contract()
        for key in ('full_action_scheduler_available','card_effects_implemented','resurrection_rules_implemented','training_label_allowed','server_parity_verified'):
            self.assertFalse(c[key])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/EVIDENCE;p.parent.mkdir(parents=True);p.write_bytes((ROOT/EVIDENCE).read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):load_action_boundary_contract(d)
