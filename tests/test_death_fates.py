from copy import deepcopy
import unittest

from yixian.death_fates import (
    AmbiguousDeathFateOrder, FIVE_ELEMENTS, UnknownDeathFateState,
    apply_death_prevention, initialize_death_fates, resolve_pending_death_fates,
)


def player(fate=7, **updates):
    result = {'life': 10, 'fates': [fate], 'rerolls': 24, 'exp': 56,
              'hand_cards': [], 'max_hp': 100, 'extra_max_hp': 46,
              'max_physique': 96}
    result.update(updates)
    return initialize_death_fates(result, talent_counters={str(fate): 1})


def five_cards(request):
    assert request['minimum_realm'] == 4
    return [{'card_id': 100 + i, 'element': element, 'realm': 4 + i % 2}
            for i, element in enumerate(FIVE_ELEMENTS)]


class DeathFateTests(unittest.TestCase):
    def test_missing_snapshot_never_creates_life(self):
        raw = {'life': 10, 'fates': [7], 'rerolls': 0}
        with self.assertRaises(UnknownDeathFateState):
            apply_death_prevention(raw, 10)
        unavailable = apply_death_prevention(raw, 10, talent_counters={})
        self.assertEqual(unavailable['life_damage'], 10)
        self.assertEqual(unavailable['events'], [])
        fresh = apply_death_prevention(raw, 10, newly_acquired_fates=(7,))
        self.assertEqual(fresh['life_damage'], 9)

    def test_only_lethal_damage_consumes_and_rerolls_can_overflow(self):
        actor = player()
        frozen = deepcopy(actor)
        lower = apply_death_prevention(actor, 9)
        self.assertEqual(lower['player']['effect_state']['death_fate_remaining']['7'], 1)
        self.assertEqual(lower['player']['rerolls'], 24)
        hit = apply_death_prevention(actor, 10)
        self.assertEqual(hit['life_damage'], 9)
        self.assertEqual(hit['player']['life'], 10)  # Caller deducts exactly once.
        self.assertEqual(hit['player']['rerolls'], 29)
        self.assertEqual(actor, frozen)

    def test_consumed_counter_cannot_reset_from_replay_or_repeated_acquisition(self):
        used = apply_death_prevention(player(), 20)['player']
        used['life'] = 1
        imported = initialize_death_fates(used, talent_counters={'7': 1}, newly_acquired_fates=(7,))
        later = apply_death_prevention(imported, 1)
        self.assertEqual(later['life_damage'], 1)
        self.assertEqual(later['player']['rerolls'], 29)
        self.assertEqual(later['events'], [])

    def test_zero_damage_after_immunity_does_not_consume(self):
        result = apply_death_prevention(player(life=1), 0)
        self.assertEqual(result['life_damage'], 0)
        self.assertEqual(result['player']['effect_state']['death_fate_remaining']['7'], 1)

    def test_dead_player_does_not_resurrect(self):
        with self.assertRaises(ValueError):
            apply_death_prevention(player(life=0), 0)

    def test_65_matches_replay_cost_and_raw_card(self):
        result = apply_death_prevention(player(65, life=2), 12)
        self.assertEqual(result['life_damage'], 1)
        self.assertEqual(result['player']['exp'], 55)
        self.assertEqual(result['player']['hand_cards'], [12])
        self.assertTrue(result['complete_resolution'])

    def test_154_increases_caps_but_does_not_change_current_battle_health(self):
        actor = player(154, life=16, hp=35, physique=40)
        result = apply_death_prevention(actor, 16)
        updated = result['player']
        self.assertEqual(result['life_damage'], 15)
        self.assertEqual([updated[x] for x in ('max_hp', 'extra_max_hp', 'max_physique')], [104, 50, 100])
        self.assertEqual([updated[x] for x in ('hp', 'physique')], [35, 40])

    def test_154_accepts_signed_extra_health_modifier(self):
        result = apply_death_prevention(player(154, max_hp=35, extra_max_hp=-5), 10)
        self.assertEqual(result['player']['extra_max_hp'], -1)
        self.assertEqual(result['player']['max_hp'], 39)

    def test_83_requires_explicit_draw_then_consumes_and_charges_once(self):
        actor = player(83)
        pending = apply_death_prevention(actor, 10)
        self.assertEqual(pending['player']['exp'], 51)
        self.assertEqual(pending['player']['hand_cards'], [])
        self.assertEqual(pending['player']['effect_state']['death_fate_remaining']['83'], 0)
        self.assertFalse(pending['complete_resolution'])
        self.assertTrue(pending['pending_actions'])
        with self.assertRaises(UnknownDeathFateState):
            apply_death_prevention(pending['player'], 1)
        resolved = resolve_pending_death_fates(pending['player'], draw_five_elements=five_cards)
        self.assertEqual(resolved['player']['exp'], 51)
        self.assertEqual(resolved['player']['hand_cards'], list(range(100, 105)))
        self.assertEqual(resolved['pending_actions'], [])
        self.assertTrue(resolved['complete_resolution'])
        twice = resolve_pending_death_fates(resolved['player'], draw_five_elements=five_cards)
        self.assertEqual(twice['player'], resolved['player'])

    def test_83_supplied_provider_resolves_in_one_operation(self):
        result = apply_death_prevention(player(83), 10, draw_five_elements=five_cards)
        self.assertEqual(result['player']['hand_cards'], list(range(100, 105)))
        self.assertTrue(result['complete_resolution'])
        self.assertFalse(result['complete_rule_execution'])

    def test_83_rejects_wrong_count_duplicate_element_or_low_realm_without_mutation(self):
        cases = [five_cards({'minimum_realm': 4})[:4],
                 [{'card_id': 100 + i, 'element': 'wood', 'realm': 4} for i in range(5)],
                 [{'card_id': 100 + i, 'element': e, 'realm': 3} for i, e in enumerate(FIVE_ELEMENTS)]]
        actor = player(83)
        frozen = deepcopy(actor)
        for cards in cases:
            with self.subTest(cards=cards), self.assertRaises(ValueError):
                apply_death_prevention(actor, 10, draw_five_elements=lambda request: cards)
            self.assertEqual(actor, frozen)

    def test_uncalibrated_ai_83_is_not_silently_given_human_reward(self):
        with self.assertRaises(UnknownDeathFateState):
            apply_death_prevention(player(83, is_ai=True), 10, draw_five_elements=five_cards)

    def test_multiple_eligible_protections_do_not_guess_consumption_order(self):
        actor = player()
        actor['fates'].append(65)
        actor = initialize_death_fates(actor, talent_counters={'65': 1})
        frozen = deepcopy(actor)
        with self.assertRaises(AmbiguousDeathFateOrder):
            apply_death_prevention(actor, 10)
        self.assertEqual(actor, frozen)

    def test_exhausted_other_protection_does_not_block_available_one(self):
        actor = initialize_death_fates(player(fates=[7, 65]), talent_counters={'65': 0})
        self.assertEqual(apply_death_prevention(actor, 10)['events'][0]['effect_id'], 7)

    def test_invalid_counter_and_missing_reward_resource_fail_without_mutation(self):
        for counter in (True, '1'):
            with self.assertRaises(ValueError):
                initialize_death_fates({'fates': [7]}, talent_counters={'7': counter})
        actor = player(154)
        del actor['max_physique']
        frozen = deepcopy(actor)
        with self.assertRaises(UnknownDeathFateState):
            apply_death_prevention(actor, 10)
        self.assertEqual(actor, frozen)


if __name__ == '__main__':
    unittest.main()
