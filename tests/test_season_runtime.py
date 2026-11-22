"""Real reference-card execution for audited seasonal components."""
import copy
import unittest

from yixian.simulator import SimulatorError, is_available, simulate_battle


def battle(ids=(), *, card='111011', turns=1, first=0, disabled=()):
    players=[{'hp':100,'max_hp':100,'cultivation':10,'round_number':12,
              'destiny':100,'cards':[card]*8,'qi':20} for _ in range(2)]
    return {'seed':7,'max_turns':turns,'first_player':first,'players':players,
            'season_runtime':[{'ids':list(ids),'disabled_ids':list(disabled)},
                              {'ids':[],'disabled_ids':[]}]}


@unittest.skipUnless(is_available(),'Requires pinned yisim')
class SeasonRuntimeTests(unittest.TestCase):
    def test_1005_blocks_chase_for_one_own_turn_without_blocking_card(self):
        source=battle([1005],card='114061',turns=3)
        first=simulate_battle(dict(source,max_turns=1))
        self.assertEqual(first['players'][0]['next_card_index'],1)
        self.assertEqual(first['players'][1]['hp'],90)
        later=simulate_battle(source)
        self.assertEqual(later['players'][0]['next_card_index'],3)
        self.assertEqual([p['no_chase_remaining'] for p in later['season_runtime']['player_state']],[0,0])

    def test_1005_is_not_bypassed_by_prevent_anti_chase(self):
        source=battle([1005],card='114061')
        source['players'][0]['prevent_anti_chase']=1
        self.assertEqual(simulate_battle(source)['players'][0]['next_card_index'],1)

    def test_1007_upgrades_only_first_eligible_battle_card(self):
        source=battle([1007],turns=3)
        before=copy.deepcopy(source)
        result=simulate_battle(source)
        self.assertEqual(source,before)
        self.assertEqual(result['players'][0]['cards'],['111012']+['111011']*7)
        self.assertEqual(result['players'][1]['hp'],85) # 9 then 6 attack
        self.assertEqual(result['season_runtime']['player_state'][0]['original_cards'],['111011']*8)

    def test_1007_keeps_charge_past_already_maximum_card(self):
        source=battle([1007],turns=3)
        source['players'][0]['cards'][0]='111013'
        result=simulate_battle(source)
        self.assertEqual(result['players'][0]['cards'][:3],['111013','111012','111011'])

    def test_1008_pays_per_attack_not_per_play(self):
        result=simulate_battle(battle([1008],card='111121'))
        self.assertEqual(result['players'][0]['hp'],96)
        self.assertEqual(result['players'][1]['hp'],94)

    def test_1009_only_upgrades_regular_cards_in_last_three_slots(self):
        source=battle([1009]);source['players'][0]['cards'][6]='601011'
        result=simulate_battle(source)
        self.assertEqual(result['players'][0]['cards'][4:],['111011','111013','601011','111013'])
        self.assertEqual(result['players'][1]['cards'][5:],['111013']*3)

    def test_toggles_and_input_player_order_are_explicit(self):
        disabled=simulate_battle(battle([1008],disabled=[1008]))
        self.assertEqual(disabled['players'][0]['hp'],100)
        result=simulate_battle(battle([3011],card='111061',first=1,turns=2))
        self.assertEqual([p['qi'] for p in result['players']],[24,22])

    def test_3004_first_incoming_attack_gets_dive_before_damage(self):
        source=battle([3004],first=1)
        result=simulate_battle(source)
        self.assertEqual(result['players'][0]['hp'],97) # floor(6 * 60%)
        event=next(e for e in result['season_runtime']['events'] if e['effect_id']==3004)
        self.assertEqual(event['phase'],'before_first_received_attack')
        result=simulate_battle(dict(source,max_turns=3))
        self.assertEqual(result['players'][0]['hp'],91) # dive expires at own turn start

    def test_3011_only_first_positive_qi_gain_gets_bonus(self):
        result=simulate_battle(battle([3011],card='111061',turns=3))
        self.assertEqual(result['players'][0]['qi'],26)
        events=[e for e in result['season_runtime']['events'] if e['effect_id']==3011]
        self.assertEqual(len(events),1)

    def test_3012_defense_after_decay_uses_round_threshold(self):
        source=battle([3012],card='111061');source['players'][0]['def']=10
        self.assertEqual(simulate_battle(source)['players'][0]['def'],7)
        source['players'][0]['round_number']=13
        self.assertEqual(simulate_battle(source)['players'][0]['def'],9)

    def test_two_negative_hp_uses_larger_hp_then_first_player(self):
        source=battle([1008],card='111011')
        source['players'][0]['hp']=source['players'][0]['max_hp']=1
        source['players'][1]['hp']=source['players'][1]['max_hp']=4
        result=simulate_battle(source)
        self.assertEqual([p['hp'] for p in result['players']],[-1,-2])
        self.assertEqual(result['winner'],0)
        self.assertTrue(result['simultaneous_negative_hp_legacy_settlement_skipped'])
        source['players'][1]['hp']=source['players'][1]['max_hp']=5
        self.assertEqual(simulate_battle(source)['winner'],0)

    def test_unsupported_1010_and_malformed_configuration_rejected(self):
        for entries in [
            [{'ids':[1010],'disabled_ids':[]},{'ids':[],'disabled_ids':[]}],
            [{'ids':[1005,1005],'disabled_ids':[]},{'ids':[],'disabled_ids':[]}],
            [{'ids':[3011],'disabled_ids':[3011]},{'ids':[],'disabled_ids':[]}],
            [{'ids':[],'disabled_ids':[],'code':'bad()'},{'ids':[],'disabled_ids':[]}],
        ]:
            source=battle();source['season_runtime']=entries
            with self.subTest(entries=entries),self.assertRaises(SimulatorError):simulate_battle(source)


if __name__=='__main__':unittest.main()
