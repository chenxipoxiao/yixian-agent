import copy
import unittest
from tests.test_full_battle import compile_fixture
from yixian import full_battle_v7 as old,full_battle_v8 as current
from yixian.simulator import SimulatorError
from yixian.terminal_damage import calculate_terminal_damage

class CurrentWindCardsTests(unittest.TestCase):
    def test_current_card_values_real_native_turns(self):
        for card,realm,initial_qi,expected_damage,expected_qi,expected_max in [
            ('642042',4,0,6,1,41),('642043',4,0,8,3,41),
            ('643021',4,1,2,0,40),('643022',4,1,6,0,40),('643023',4,1,12,0,40),
            ('644041',4,0,4,0,42),('644041',5,0,8,0,42)]:
            b=compile_fixture()['battle'];b['players'][0]['cards'][0]=card;b['max_turns']=1
            b['players'][0]['qi']=initial_qi
            b['current_rules_context']={'realms':[realm,1]}
            r=current.simulate_batch([b])['results'][0]
            with self.subTest(card=card,realm=realm):
                self.assertEqual(r['players'][1]['hp'],40-expected_damage)
                self.assertEqual(r['players'][0]['qi'],expected_qi)
                self.assertEqual(r['players'][0]['max_hp'],expected_max)

    def test_wind_flash_without_realm_does_not_guess(self):
        b=compile_fixture()['battle'];b['players'][0]['cards'][0]='644041'
        with self.assertRaisesRegex(SimulatorError,'explicit start realm'):current.simulate_batch([b])

    def test_official_limit_is_terminal_but_smaller_budget_is_not(self):
        for budget,terminal in [(63,False),(64,True),(128,True)]:
            c=compile_fixture();b=c['battle'];b['max_turns']=budget
            for p in b['players']:p.update(hp=10000,max_hp=10000)
            r=current.simulate_batch([b])['results'][0]
            self.assertEqual(r['turns'],min(budget,64));self.assertEqual(r['terminated'],terminal)
            self.assertEqual(r['winner'],b['first_player'] if terminal else None)
            self.assertEqual(calculate_terminal_damage(c,r)['resolved'],terminal)
            self.assertFalse(r['training_label_allowed'])

    def test_both_alive_at_limit_use_remaining_hp(self):
        b=compile_fixture()['battle'];b['max_turns']=64
        b['players'][0].update(hp=10000,max_hp=10000)
        b['players'][1].update(hp=11000,max_hp=11000)
        r=current.simulate_batch([b])['results'][0]
        self.assertEqual(r['winner'],1);self.assertEqual(r['hp_delta'],-1000)
        self.assertEqual(r['termination_reason'],'official_64_action_limit')

    def test_unaffected_earlier_battle_is_identical(self):
        b=compile_fixture()['battle'];a=old.simulate_batch([b])['results'][0]
        r=current.simulate_batch([b])['results'][0]
        r.pop('current_wind_cards');r.pop('termination_reason')
        self.assertEqual(a,r)
