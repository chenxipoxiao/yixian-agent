from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from yixian.combat_initialization import ROOT, IncompleteCombatState
from yixian.combat_death_guard import (
    EVIDENCE, TURN_END_BOUNDARY, load_death_guard_contract,
    derive_death_guard_opening, check_death_boundary, cleanup_guard_at_turn_end,
)


def public(buffs=None):
    return {'level': 1, 'lastRoundData': {'level': 1, 'extraMaxHp': 0, 'usedCards': [1],
            'usedKeYinCards': [], 'permanentBuffTempDatas': {} if buffs is None else buffs}}


def state(hp, buffs=None):
    return {'hp': hp, 'raw_buffs': {} if buffs is None else buffs}


class DeathGuardTests(unittest.TestCase):
    def test_opening_imports_only_positive17_without_healing(self):
        r=derive_death_guard_opening(public({'17':3,'18':8,'10023':5,'10024':20}))
        self.assertEqual(r['guard_opening_combat']['raw_buffs'],{'17':3,'10023':5,'10024':20})
        self.assertEqual((r['guard_opening_combat']['hp'],r['guard_opening_combat']['max_hp']),(40,45))
        self.assertNotIn('17',r['initialized_combat']['raw_buffs'])
        self.assertFalse(r['initiative_inferred_from_guard'])

    def test_empty_zero_and_negative_permanent17_do_not_arm(self):
        for buffs in ({},{'17':0},{'17':-1}):
            with self.subTest(buffs=buffs):
                self.assertNotIn('17',derive_death_guard_opening(public(buffs))['guard_opening_combat']['raw_buffs'])

    def test_processed17_is_not_queued_again_at_later_boundary(self):
        for value in (1,0,-1):
            r=derive_death_guard_opening(public({'17':value,'18':1,'369':3}))
            self.assertNotIn('17',r['deferred_permanent_entries'])
            self.assertEqual(r['deferred_permanent_entries'],{'18':1,'369':3})
            self.assertEqual(r['initdata_deferred_permanent_entries']['17'],value)

    def test_missing_map_is_not_inferred_from_tied_speed_or_recorded_second(self):
        p=public();del p['lastRoundData']['permanentBuffTempDatas'];p.update(firstPlayerId='other',speed=10)
        with self.assertRaises(IncompleteCombatState):derive_death_guard_opening(p)

    def test_current_future_and_unrelated_permanent_flags_do_not_arm(self):
        p=public({'10006':1});p.update(permanentBuffTempDatas={'17':1},winner='future')
        self.assertNotIn('17',derive_death_guard_opening(p)['guard_opening_combat']['raw_buffs'])

    def test_opening_rejects_evolved_boundary_instead_of_rearming(self):
        evolved=derive_death_guard_opening(public({'17':1}))
        with self.assertRaises(IncompleteCombatState):derive_death_guard_opening(evolved)

    def test_hp_one_does_not_consume(self):
        r=check_death_boundary([state(1,{'17':1}),state(10)])
        self.assertEqual(r['players'][0]['raw_buffs'],{'17':1});self.assertFalse(r['candidate_death_check'])

    def test_zero_hp_triggers_and_does_not_heal(self):
        r=check_death_boundary([state(0,{'17':1}),state(10)])
        self.assertEqual(r['players'][0],state(0,{'18':1}));self.assertFalse(r['candidate_death_check'])

    def test_negative_hp_is_preserved_with_guard(self):
        r=check_death_boundary([state(-400,{'17':1}),state(10)])
        self.assertEqual(r['players'][0]['hp'],-400);self.assertFalse(r['hp_was_clamped'])

    def test_entire17_removed_not_one_stack_spent(self):
        r=check_death_boundary([state(-1,{'17':8}),state(10)])
        self.assertEqual(r['players'][0]['raw_buffs'],{'18':1})

    def test_repeated_check_does_not_rearm_or_increment_guard(self):
        r=check_death_boundary([state(-1,{'17':1}),state(10)])
        repeated=check_death_boundary(r['players'])
        self.assertEqual(repeated['players'],r['players']);self.assertEqual(repeated['events'],[])

    def test_existing18_increments_only_on_new17_consumption(self):
        r=check_death_boundary([state(-1,{'17':1,'18':3}),state(10)])
        self.assertEqual(r['players'][0]['raw_buffs'],{'18':4})

    def test_hasbuff_uses_key_presence_even_zero_or_negative(self):
        for value in (0,-1):
            with self.subTest(value=value):
                r=check_death_boundary([state(-1,{'17':value}),state(10)])
                self.assertEqual(r['players'][0]['raw_buffs'],{'18':1})
                self.assertFalse(check_death_boundary([state(-1,{'18':value}),state(10)])['candidate_death_check'])

    def test_modify18_removes_nonpositive_result(self):
        r=check_death_boundary([state(-1,{'17':1,'18':-1}),state(10)])
        self.assertEqual(r['players'][0]['raw_buffs'],{});self.assertTrue(r['candidate_death_check'])

    def test_no_guard_and_zero_or_negative_hp_returns_death_check_true(self):
        for hp in (0,-1):
            self.assertTrue(check_death_boundary([state(hp),state(10)])['candidate_death_check'])

    def test_both_alive_no_guard_returns_false(self):
        self.assertFalse(check_death_boundary([state(1),state(1)])['candidate_death_check'])

    def test_left_short_circuit_keeps_right17_unconsumed(self):
        r=check_death_boundary([state(-4,{'17':1}),state(-3,{'17':1})])
        self.assertEqual(r['checked_player_indices'],[0]);self.assertEqual(r['players'][1]['raw_buffs'],{'17':1})
        self.assertEqual(r['deferred_by_player_index'],0)

    def test_right_guard_checked_when_left_has_higher_hp(self):
        r=check_death_boundary([state(-3,{'17':1}),state(-4,{'17':1})])
        self.assertEqual(r['checked_player_indices'],[0,1]);self.assertEqual(r['deferred_by_player_index'],1)
        self.assertEqual([p['raw_buffs'] for p in r['players']],[{'18':1},{'18':1}])

    def test_active_guard_does_not_prevent_opponent_with_lower_hp_ending(self):
        r=check_death_boundary([state(-3,{'18':1}),state(-9)])
        self.assertTrue(r['candidate_death_check']);self.assertIsNone(r['winner_index'])

    def test_equal_negative_hp_is_deferred_for_guard_holder(self):
        r=check_death_boundary([state(-3),state(-3,{'17':1})])
        self.assertFalse(r['candidate_death_check']);self.assertEqual(r['deferred_by_player_index'],1)

    def test_cleanup_affects_owner_only_and_keeps_unconsumed17(self):
        r=cleanup_guard_at_turn_end([state(-1,{'17':2,'18':1}),state(-2,{'18':1})],actor_index=0,boundary=TURN_END_BOUNDARY)
        self.assertEqual([p['raw_buffs'] for p in r['players']],[{'17':2},{'18':1}])
        self.assertTrue(r['remaining_turn_end_hooks_required']);self.assertTrue(r['following_death_check_required'])

    def test_unconsumed17_survives_turn_end(self):
        r=cleanup_guard_at_turn_end([state(10,{'17':1}),state(10)],actor_index=0,boundary=TURN_END_BOUNDARY)
        self.assertEqual(r['players'][0]['raw_buffs'],{'17':1})

    def test_lethal_guard_cleanup_then_following_check_ends_candidate(self):
        r=check_death_boundary([state(-1,{'17':1}),state(10)])
        ended=cleanup_guard_at_turn_end(r['players'],actor_index=0,boundary=TURN_END_BOUNDARY)
        self.assertTrue(check_death_boundary(ended['players'])['candidate_death_check'])

    def test_healing_before_cleanup_can_leave_candidate_alive_without_rearming(self):
        r=check_death_boundary([state(-1,{'17':1}),state(10)]);r['players'][0]['hp']=1
        ended=cleanup_guard_at_turn_end(r['players'],actor_index=0,boundary=TURN_END_BOUNDARY)
        self.assertFalse(check_death_boundary(ended['players'])['candidate_death_check'])
        ended['players'][0]['hp']=-1
        self.assertTrue(check_death_boundary(ended['players'])['candidate_death_check'])

    def test_cleanup_rejects_card_and_extra_action_end_boundaries(self):
        for boundary in ('OnCardEnd','extra_action_end','OnTurnStarted',None):
            with self.subTest(boundary=boundary),self.assertRaises(IncompleteCombatState):
                cleanup_guard_at_turn_end([state(0),state(1)],actor_index=0,boundary=boundary)

    def test_cleanup_rejects_invalid_actor(self):
        for actor in (True,-1,2,'0'):
            with self.subTest(actor=actor),self.assertRaises(IncompleteCombatState):
                cleanup_guard_at_turn_end([state(0),state(1)],actor_index=actor,boundary=TURN_END_BOUNDARY)

    def test_missing_or_malformed_state_rejects(self):
        invalid=[{},state(True),state(1.5),{'hp':1},state(1,{17:1}),state(1,{'017':1}),state(1,{'17':True}),state(1,{'17':1.2})]
        for p in invalid:
            with self.subTest(player=p),self.assertRaises(IncompleteCombatState):check_death_boundary([p,state(1)])
        for players in ([],[state(1)],[state(1)]*3,{}):
            with self.subTest(players=players),self.assertRaises(IncompleteCombatState):check_death_boundary(players)

    def test_excess_values_reject_without_mutating(self):
        players=[state(0,{'17':1,'18':1_000_000}),state(1)];old=deepcopy(players)
        with self.assertRaises(IncompleteCombatState):check_death_boundary(players)
        self.assertEqual(players,old)

    def test_all_functions_reject_unscoped_modes(self):
        for mode in (16,True,'3'):
            for fn in (lambda:derive_death_guard_opening(public(),game_mode=mode),
                       lambda:check_death_boundary([state(1),state(1)],game_mode=mode),
                       lambda:cleanup_guard_at_turn_end([state(1),state(1)],actor_index=0,boundary=TURN_END_BOUNDARY,game_mode=mode)):
                with self.subTest(mode=mode),self.assertRaises(IncompleteCombatState):fn()

    def test_inputs_and_unrelated_fields_are_preserved(self):
        players=[state(0,{'17':1,'10023':8}),state(1)];players[0]['max_hp']=50;old=deepcopy(players)
        r=check_death_boundary(players);cleanup_guard_at_turn_end(r['players'],actor_index=0,boundary=TURN_END_BOUNDARY)
        self.assertEqual(players,old);self.assertEqual(r['players'][0]['max_hp'],50)
        self.assertEqual(r['players'][0]['raw_buffs']['10023'],8)

    def test_contract_hash_and_no_training_or_winner_claim(self):
        c=load_death_guard_contract();r=check_death_boundary([state(-1),state(10)])
        for obj in (c,r,derive_death_guard_opening(public())):
            for key in ('server_parity_verified','training_label_allowed','settlement_allowed','counterfactual_safe'):
                self.assertFalse(obj[key])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/EVIDENCE;p.parent.mkdir(parents=True);p.write_bytes((ROOT/EVIDENCE).read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):load_death_guard_contract(d)
