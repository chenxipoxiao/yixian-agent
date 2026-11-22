from copy import deepcopy
import unittest

from yixian.effect_battle import simulate_effect_battle
from yixian.effects import EffectEngine
from yixian.simulator import is_available


def fixture(max_turns=1):
    return {'seed':73,'max_turns':max_turns,'first_player':0,'players':[
        {'character':'sw1','hp':40,'max_hp':40,'cultivation':10,'round_number':10,'destiny':100,'cards':['111071']*8},
        {'character':'sw2','hp':40,'max_hp':40,'cultivation':9,'round_number':10,'destiny':100,'cards':['601011']*8}]}


def states(engine, enabled=True):
    return [engine.initialize_player({'life':100,'rerolls':25,'fates':[],'season_choices':[1001,2011]},
                                     season_temp_datas={'1001':0 if enabled else 1}),
            engine.initialize_player({'life':100,'rerolls':0,'fates':[45,105],'season_choices':[]},talent_counters={'105':1})]


@unittest.skipUnless(is_available(),'Pinned legacy simulator is not installed')
class EffectBattleTests(unittest.TestCase):
    def test_start_qi_changes_actual_card_execution(self):
        engine=EffectEngine(); battle=fixture(); active=states(engine); before=deepcopy(active)
        on=simulate_effect_battle(battle,active,engine=engine)
        off=simulate_effect_battle(battle,states(engine,False),engine=engine)
        self.assertEqual(on['starting_qi'],[2,2])
        self.assertEqual(off['starting_qi'],[0,0])
        self.assertLess(on['combat']['players'][1]['hp'],off['combat']['players'][1]['hp'])
        self.assertEqual(active,before)

    def test_capped_battle_cannot_consume_guard_or_grant_rerolls(self):
        engine=EffectEngine(); initial=states(engine)
        result=simulate_effect_battle(fixture(),initial,engine=engine)
        self.assertFalse(result['label_usable'])
        self.assertIsNone(result['settlement'])
        self.assertEqual(result['match_players'],initial)

    def test_legacy_destiny_is_discarded_and_effect_settlement_applied_once(self):
        engine=EffectEngine();initial=states(engine)
        result=simulate_effect_battle(fixture(64),initial,engine=engine)
        self.assertTrue(result['label_usable'])
        self.assertEqual(result['combat']['winner'],0)
        self.assertTrue(result['legacy_destiny_settlement_discarded'])
        self.assertNotIn('destiny',result['combat']['players'][1])
        self.assertEqual(result['match_players'][1]['life'],100-result['settlement']['life_damage'])
        self.assertEqual(result['match_players'][0]['rerolls'],26)

    def test_combat_destiny_cards_are_rejected_until_their_state_is_preserved(self):
        battle=fixture(); battle['players'][0]['cards'][0]='402011'
        with self.assertRaises(ValueError):
            simulate_effect_battle(battle,states(EffectEngine()))

    def test_standalone_battle_expires_overflow_before_new_reward(self):
        engine=EffectEngine(); initial=states(engine);initial[0]['rerolls']=28
        result=simulate_effect_battle(fixture(),initial,engine=engine)
        self.assertEqual(result['match_players'][0]['rerolls'],25)
        self.assertEqual(result['reroll_overflow_cleanup'][0]['before'],28)
