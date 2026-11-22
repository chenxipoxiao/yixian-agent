from copy import deepcopy
import random
import unittest

from yixian.round_rules import (
    RULE_SOURCES, draw_from_combined_remaining, ordinary_destiny_damage,
    overflow_conversion, reroll_grant, round_draw_requests, round_resource_plan,
    round_rules_contract, select_terminal_winner,
)
from yixian.settlement import ordinary_destiny_damage as original_destiny_damage


class FixedIndex:
    def __init__(self, index):
        self.index = index
        self.sizes = []

    def randrange(self, size):
        self.sizes.append(size)
        return self.index


class RoundRulesTests(unittest.TestCase):
    def test_ordinary_reroll_boundaries_and_season_round13_override(self):
        for number, expected in ((1,3),(9,3),(10,4),(12,4),(13,4),(14,4),(15,5),(19,5),(20,6),(99,6)):
            self.assertEqual(reroll_grant(number, False), expected)
        for number, expected in ((1,3),(9,3),(10,4),(12,4),(13,6),(14,6),(15,6),(19,6),(20,6)):
            self.assertEqual(reroll_grant(number), expected)

    def test_draw_extra_begins_on_round12_after_ordinary_draws(self):
        before = round_draw_requests(11)
        after = round_draw_requests(12)
        self.assertEqual([(x["pool"],x["count"]) for x in before], [("sect",2),("profession",1)])
        self.assertEqual(after[:2], before)
        self.assertEqual(after[2]["pool"], "combined_remaining")
        self.assertEqual(after[2]["count"], 1)
        self.assertEqual(after[2]["sampling"], "uniform_remaining_card_entity")
        self.assertTrue(after[2]["after_previous_requests"])

    def test_one_excess_hand_card_converts_exactly_one_round_start_draw(self):
        for number, expected in ((1,3),(11,3),(12,4),(13,4),(20,4)):
            with self.subTest(round=number):
                normal = overflow_conversion(number, 12)
                excess = overflow_conversion(number, 13)
                self.assertEqual(sum(x["count"] for x in normal["draw_requests"]), expected)
                self.assertEqual(normal["cultivation_gain"], 0)
                self.assertEqual(sum(x["count"] for x in excess["draw_requests"]), expected-1)
                self.assertEqual(excess["converted_card_count"], 1)
                self.assertEqual(excess["cultivation_gain"], 1)
                self.assertFalse(excess["pending"])
                self.assertEqual(excess["source_kind"], "user_confirmed")

    def test_growth_separates_conversion_so_caller_can_avoid_double_credit(self):
        plan = round_resource_plan(13, 13)
        self.assertEqual((plan["base_cultivation"],plan["converted_cultivation"],plan["total_cultivation"]), (2,1,3))
        self.assertEqual((plan["max_hp_gain"],plan["reroll_grant"]), (2,6))
        self.assertFalse(plan["state_committed"])
        self.assertEqual(round_resource_plan(1,0)["total_cultivation"],2)

    def test_round_start_removes_tail_preserving_category_order(self):
        expected={
            11:{12:['sect','sect','profession'],13:['sect','sect'],14:['sect'],15:[],16:[]},
            12:{12:['sect','sect','profession','combined_remaining'],13:['sect','sect','profession'],
                14:['sect','sect'],15:['sect'],16:[]}}
        for number,hand_cases in expected.items():
            all_cards=hand_cases[12]
            for hand,kept in hand_cases.items():
                with self.subTest(round=number,hand=hand):
                    plan=overflow_conversion(number,hand)
                    expand=lambda rs:[r['pool'] for r in rs for _ in range(r['count'])]
                    self.assertEqual(expand(plan['draw_requests']),kept)
                    self.assertEqual(expand(plan['converted_draw_requests']),all_cards[len(kept):])
                    self.assertEqual(plan['cultivation_gain'],len(all_cards)-len(kept))
                    self.assertEqual(plan['actual_draw_count'],len(kept))

    def test_very_large_hand_cannot_convert_more_than_scheduled_draws(self):
        for number,expected in ((1,3),(12,4)):
            plan=overflow_conversion(number,99)
            self.assertEqual(plan['draw_requests'],[])
            self.assertEqual(plan['cultivation_gain'],expected)
            self.assertEqual(plan['applies_to'],'ordinary_round_start_only')

    def test_draw_count_and_conversion_conserve_each_rounds_grant(self):
        for number in (1,11,12,13,20):
            for hand in range(25):
                plan=overflow_conversion(number,hand)
                self.assertEqual(plan['actual_draw_count']+plan['cultivation_gain'],plan['scheduled_card_count'])
                self.assertGreaterEqual(plan['actual_draw_count'],0)

    def test_combined_draw_indexes_entities_without_category_coin_flip(self):
        sect, profession = [101,101,102], [201]
        frozen = deepcopy((sect,profession))
        outcomes = []
        for index in range(4):
            rng = FixedIndex(index)
            drawn = draw_from_combined_remaining(sect, profession, rng=rng)
            outcomes.append((drawn["card"],drawn["pool"]))
            self.assertEqual(rng.sizes,[4])
            self.assertEqual(len(drawn["remaining_sect_pool"])+len(drawn["remaining_profession_pool"]),3)
        self.assertEqual(outcomes,[(101,"sect"),(101,"sect"),(102,"sect"),(201,"profession")])
        self.assertEqual((sect,profession),frozen)

    def test_combined_draw_has_reproducible_seed_and_handles_one_empty_pool(self):
        left = draw_from_combined_remaining([1,2,3],[4],rng=random.Random(831))
        right = draw_from_combined_remaining([1,2,3],[4],rng=random.Random(831))
        self.assertEqual(left,right)
        self.assertEqual(draw_from_combined_remaining([], [4], rng=FixedIndex(0))["card"],4)
        with self.assertRaises(ValueError):
            draw_from_combined_remaining([], [], rng=FixedIndex(0))

    def test_terminal_must_be_confirmed_before_any_winner_is_selected(self):
        for hps in ((10,-2),(-2,10),(-1,-2),(-2,-2)):
            result=select_terminal_winner(hps,0,False)
            self.assertFalse(result["resolved"])
            self.assertIsNone(result["winner"])
            self.assertEqual(result["reason"],"terminal_not_confirmed")

    def test_both_negative_choose_higher_hp_then_first_player(self):
        self.assertEqual(select_terminal_winner([-2,-7],1,True)["winner"],0)
        self.assertEqual(select_terminal_winner([-7,-2],0,True)["winner"],1)
        for first in (0,1):
            result=select_terminal_winner([-3,-3],first,True)
            self.assertTrue(result["resolved"])
            self.assertEqual(result["winner"],first)
            self.assertEqual(result["reason"],"equal_negative_hp_first_player")

    def test_single_survivor_and_unverified_zero_boundaries(self):
        for hps,winner in (([5,-1],0),([-1,5],1),([5,0],0),([0,5],1)):
            self.assertEqual(select_terminal_winner(hps,1,True)["winner"],winner)
        for hps in ([0,0],[0,-1],[-1,0],[1,1]):
            result=select_terminal_winner(hps,0,True)
            self.assertFalse(result["resolved"])
            self.assertIsNone(result["winner"])

    def test_invalid_inputs_cannot_generate_resources_or_labels(self):
        for number in (0,-1,True,1.2,"12"):
            for fn in (reroll_grant,round_draw_requests):
                with self.subTest(number=number,fn=fn.__name__),self.assertRaises(ValueError):
                    fn(number)
        for hand in (-1,True,2.5):
            with self.assertRaises(ValueError):
                overflow_conversion(12,hand)
        with self.assertRaises(ValueError):
            reroll_grant(13,1)
        for hps in ([float("nan"),-1],[float("inf"),-1],[True,-1],[1]):
            with self.assertRaises(ValueError):
                select_terminal_winner(hps,0,True)
        for first,terminal in ((True,True),(2,True),(0,1)):
            with self.assertRaises(ValueError):
                select_terminal_winner([-1,-2],first,terminal)

    def test_damage_is_reused_and_source_tags_do_not_claim_server_verification(self):
        self.assertIs(ordinary_destiny_damage,original_destiny_damage)
        contract=round_rules_contract()
        self.assertFalse(contract["current_server_verified"])
        self.assertFalse(contract["ordinary_draw_sampling_distribution_implemented"])
        self.assertEqual(RULE_SOURCES["season_rerolls"]["kind"],"user_confirmed")
        contract["sources"]["hand_overflow"]["kind"]="altered"
        self.assertEqual(RULE_SOURCES["hand_overflow"]["kind"],"user_confirmed")


if __name__ == "__main__":
    unittest.main()
