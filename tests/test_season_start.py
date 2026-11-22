from copy import deepcopy
import unittest

from yixian.effects import EffectEngine
from yixian.effect_battle import simulate_effect_battle
from yixian.simulator import is_available


def player(effects=(), **extra):
    return dict({'life':50,'hp':53,'max_hp':60,'qi':0,'cultivation':10,'rerolls':3,
                 'fates':[],'season_choices':list(effects),'hand_cards':[]}, **extra)


class SeasonStartTests(unittest.TestCase):
    def setUp(self):
        self.engine = EffectEngine()

    def start(self, effects, **extra):
        return self.engine.battle_start(player(effects,**extra),player())['players']

    def test_percentage_uses_current_health_floor_and_order(self):
        left,right = self.start([1003,1006])
        # floor(53*.15)=7, then floor(60*.15)=9; maximum gets the same deltas.
        self.assertEqual((left['hp'],left['max_hp']),(51,58))
        self.assertEqual((right['hp'],right['max_hp']),(51,58))

    def test_duplicate_owner_effects_stack_without_persistent_changes(self):
        source = player([1002,1004]); before=deepcopy(source)
        result=self.engine.battle_start(source,source)
        self.assertEqual([p['increase_atk'] for p in result['players']],[2,2])
        self.assertEqual([p['internal_injury'] for p in result['players']],[6,6])
        self.assertEqual(source,before)

    def test_switch_state_is_not_refilled_by_replay(self):
        source=self.engine.initialize_player(player([1002,7036]),season_temp_datas={'1002':1,'7036':1})
        source=self.engine.initialize_player(source,season_temp_datas={})
        me,enemy=self.engine.battle_start(source,player())['players']
        self.assertNotIn('increase_atk',enemy)
        self.assertNotIn('hexproof',me)
        self.assertEqual(me['hp'],60)  # Healing remains active while hexproof is off.
        enabled=self.engine.set_season_enabled(source,7036,True)
        self.assertEqual(self.engine.battle_start(enabled,player())['players'][0]['hexproof'],2)

    def test_element_marks_and_enemy_changes(self):
        me,enemy=self.start([3001,3002,7066,7095,7096,7098,7105])
        self.assertEqual((me['qi'],me['def'],me['penetrate'],me['guard_up'],me['styx']),(2,8,4,1,2))
        for element in ('wood','earth','metal','fire'):
            self.assertEqual(me[f'activate_{element}_spirit_stacks'],1)
        self.assertEqual((enemy['decrease_atk'],enemy['hp'],enemy['max_hp']),(1,49,56))
        self.assertEqual(me['max_hp'],60)  # 3002 acquisition reward isn't applied again.

    def test_condition_boundaries(self):
        self.assertEqual(self.start([7123],life=50)[0]['hp'],60)
        self.assertEqual(self.start([7123],life=51)[0]['hp'],53)
        self.assertEqual(self.start([7103])[0]['hp'],58)
        self.assertEqual(self.start([15018],hand_cards=[12])[0]['hp'],59)
        self.assertEqual(self.start([15018],hand_cards=[])[0]['hp'],53)
        self.assertEqual(self.start([7078],cultivation=15)[0]['star_power'],2)
        self.assertEqual(self.start([7078],cultivation=14)[0]['star_power'],1)

    def test_missing_hand_is_not_guessed(self):
        source=player([15018]); del source['hand_cards']
        with self.assertRaisesRegex(ValueError,'explicit current hand'):
            self.engine.battle_start(source,player())

    @unittest.skipUnless(is_available(),'Pinned simulator unavailable')
    def test_attack_and_guard_enter_actual_card_combat(self):
        battle={'seed':9,'max_turns':1,'first_player':0,'players':[
            {'character':'sw1','hp':40,'max_hp':40,'cultivation':10,'round_number':8,'destiny':100,'cards':['111011']*8},
            {'character':'sw2','hp':40,'max_hp':40,'cultivation':9,'round_number':8,'destiny':100,'cards':['601011']*8}]}
        states=[player(life=100),player(life=100)]
        base=simulate_effect_battle(battle,states,engine=self.engine)
        states[0]['season_choices']=[1002]
        boosted=simulate_effect_battle(battle,states,engine=self.engine)
        self.assertLess(boosted['combat']['players'][1]['hp'],base['combat']['players'][1]['hp'])
        states[1]['season_choices']=[3002]
        guarded=simulate_effect_battle(battle,states,engine=self.engine)
        self.assertEqual(guarded['combat']['players'][1]['hp'],40)


if __name__ == '__main__':
    unittest.main()
