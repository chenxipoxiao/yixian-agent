from copy import deepcopy
import json
import random
import unittest

from yixian.card_pool import (create_pool, draw_card, replace_card, generate_card,
                              refine_card, metadata_from_local, snapshot, contract)


def card(card_id, realm=1, category='sect', copies=8, family=None, replace_effect=False):
    return {'card_id': card_id, 'name': family or f'card-{card_id}',
            'family': family or f'card-{card_id}', 'realm': realm, 'category': category,
            'copy_count': copies, 'replace_effect': replace_effect}


def pool(cards=None, seed=1, timing='before_draw', season=True):
    return create_pool(cards or [card(1), card(2, realm=2)], seed=seed,
                       removal_timing=timing, season_extra_removal=season)


class CardPoolTests(unittest.TestCase):
    def test_independent_players_games_and_input_not_mutated(self):
        first, second = pool(), pool()
        frozen = deepcopy(first)
        result = draw_card(first, [1])
        self.assertEqual(result['pool']['families']['card-1']['remaining'], 7)
        self.assertEqual(first, frozen)
        self.assertEqual(second, frozen)
        self.assertEqual(pool(), frozen)

    def test_persistent_rng_and_json_restart_are_reproducible(self):
        initial = pool()
        one = draw_card(initial, [2, 1])
        restored = json.loads(json.dumps(one['pool']))
        self.assertEqual(draw_card(restored, [1, 2]), draw_card(one['pool'], [2, 1]))
        self.assertEqual(draw_card(initial, [1, 2]), one)

    def test_explicit_rng_is_cloned_and_seed_and_rng_are_exclusive(self):
        rng = random.Random(19)
        frozen = rng.getstate()
        result = create_pool([card(1)], rng=rng, removal_timing='before_draw')
        draw_card(result, [1])
        self.assertEqual(rng.getstate(), frozen)
        with self.assertRaises(ValueError):
            create_pool([card(1)], seed=1, rng=rng, removal_timing='before_draw')
        with self.assertRaises(ValueError):
            create_pool([card(1)], removal_timing='before_draw')

    def test_draw_consumes_but_generate_and_refine_leave_pool_unchanged(self):
        initial = pool()
        drawn = draw_card(initial, [1])['pool']
        self.assertEqual(generate_card(drawn, 999999)['pool'], drawn)
        self.assertEqual(refine_card(drawn, 1)['pool'], drawn)
        self.assertEqual(drawn['families']['card-1']['remaining'], 7)

    def test_season_sect_removes_three_profession_two_and_ordinary_sect_two(self):
        cases = [('sect', True, 5), ('profession', True, 6), ('sect', False, 6)]
        for category, season, remaining in cases:
            with self.subTest(category=category, season=season):
                initial = pool([card(1, category=category), card(2)], season=season)
                result = replace_card(initial, 1, [2], round_number=1, realm=1)
                self.assertEqual(result['pool']['families']['card-1']['remaining'], remaining)
                self.assertEqual(result['pool']['families']['card-2']['remaining'], 7)

    def test_replace_effect_exempts_removal_but_does_not_claim_effect_execution(self):
        initial = pool([card(1, replace_effect=True), card(2)])
        result = replace_card(initial, 1, [2], round_number=1, realm=1)
        self.assertEqual(result['pool']['families']['card-1']['remaining'], 8)
        self.assertFalse(result['replacement_card_effects_executed'])

    def test_first_replace_returns_off_realm_card_once_and_second_low_result_accepted(self):
        initial = pool([card(1, category='profession'), card(2, realm=1)])
        result = replace_card(initial, 1, [2], round_number=1, realm=2)
        self.assertTrue(result['redrawn'])
        self.assertEqual(result['card_id'], 2)  # No current-realm card exists.
        self.assertEqual(result['pool']['families']['card-2']['remaining'], 7)
        self.assertEqual(sum(e['kind'] == 'pool_draw' for e in result['events']), 2)
        self.assertEqual(sum(e['kind'] == 'first_replace_return' for e in result['events']), 1)

    def test_current_realm_first_draw_is_kept_without_redraw(self):
        result = replace_card(pool(), 1, [2], round_number=1, realm=2)
        self.assertFalse(result['redrawn'])
        self.assertEqual(sum(e['kind'] == 'pool_draw' for e in result['events']), 1)

    def test_first_replace_ledger_survives_snapshot_and_resets_only_for_new_round(self):
        initial = pool([card(1), card(2)])
        first = replace_card(initial, 1, [2], round_number=3, realm=2)
        again = replace_card(json.loads(json.dumps(first['pool'])), 1, [2], round_number=3, realm=2)
        self.assertTrue(first['redrawn'])
        self.assertFalse(again['first_replacement'])
        self.assertFalse(again['redrawn'])
        new_round = replace_card(again['pool'], 1, [2], round_number=4, realm=2)
        self.assertTrue(new_round['redrawn'])
        with self.assertRaises(ValueError):
            replace_card(new_round['pool'], 1, [2], round_number=3, realm=2)

    def test_first_replace_at_other_realm_does_not_grant_redraw_after_same_round_ascend(self):
        first = replace_card(pool([card(1), card(2)]), 1, [2], round_number=1, realm=1)
        second = replace_card(first['pool'], 1, [2], round_number=1, realm=2)
        self.assertFalse(second['redrawn'])
        for realm in (1, 5, 6):
            result = replace_card(pool([card(1), card(2)]), 1, [2], round_number=1, realm=realm)
            self.assertFalse(result['redrawn'])

    def test_empty_legal_pool_returns_exact_fallback_without_consuming_other_families(self):
        initial = pool([card(1, copies=0), card(2)])
        result = draw_card(initial, [1])
        self.assertEqual(result['card_id'], -1)
        self.assertEqual(result['pool'], initial)
        self.assertEqual(draw_card(initial, [])['card_id'], -1)

    def test_same_name_exclusion_makes_removal_order_equivalent(self):
        before = replace_card(pool([card(1, copies=2)], timing='before_draw'), 1, [1], round_number=1, realm=1)
        after = replace_card(pool([card(1, copies=2)], timing='after_draw'), 1, [1], round_number=1, realm=1)
        self.assertEqual(before['card_id'], -1)
        self.assertEqual(after['card_id'], -1)
        self.assertEqual(before['pool']['families']['card-1']['remaining'], 0)
        self.assertEqual(after['pool']['families']['card-1']['remaining'], 0)
        self.assertEqual(create_pool([card(1)], seed=1)['rules']['removal_timing'], 'before_draw')

    def test_replace_excludes_same_name_across_families_and_upgrades_both_draws(self):
        original = card(1, family='base')
        upgraded = card(10001, family='base')
        namesake = card(99, family='different')
        namesake['name'] = original['name']
        initial = pool([original, upgraded, namesake, card(2)])
        result = replace_card(initial, 1, [10001, 99, 2], round_number=1, realm=2)
        self.assertTrue(result['redrawn'])
        self.assertEqual(result['card_id'], 2)
        draws = [e['card_id'] for e in result['events'] if e['kind'] == 'pool_draw']
        self.assertEqual(draws, [2, 2])
        self.assertEqual(result['pool']['families']['different']['remaining'], 8)
        self.assertEqual(result['pool']['families']['base']['remaining'], 5)

    def test_refine_returns_basic_cultivation_and_marks_extra_effect_pending(self):
        rows = metadata_from_local([2000012, 7000112])
        initial = pool(rows)
        special = refine_card(initial, 2000012)
        self.assertEqual(special['cultivation_gain'], 1)
        self.assertTrue(special['pending_actions'])
        self.assertFalse(special['complete_refinement'])
        self.assertEqual(special['pool'], initial)
        ordinary = refine_card(initial, 7000112)
        self.assertEqual(ordinary['cultivation_gain'], 1)
        self.assertEqual(ordinary['pending_actions'], [])
        self.assertTrue(ordinary['complete_refinement'])

    def test_practice_writing_can_replace_into_itself_without_extra_pool_removal(self):
        initial = pool(metadata_from_local([6000002]))
        result = replace_card(initial, 6000002, [6000002], round_number=1, realm=2)
        self.assertEqual(result['card_id'], 6000002)
        self.assertTrue(result['redrawn'])  # Both attempts may return 练笔.
        family = initial['cards']['6000002']['family']
        self.assertEqual(result['pool']['families'][family]['remaining'], 7)
        removals = [e for e in result['events'] if e['kind'] == 'replace_pool_removal']
        self.assertEqual(removals[0]['removed'], 0)

    def test_five_elements_jade_is_replace_effect_but_deletes_three_sect_copies(self):
        initial = pool(metadata_from_local([7000109, 7000112]))
        result = replace_card(initial, 7000109, [7000109, 7000112], round_number=1, realm=2)
        self.assertEqual(result['card_id'], 7000112)
        family = initial['cards']['7000109']['family']
        self.assertTrue(initial['cards']['7000109']['replace_effect'])
        self.assertEqual(result['pool']['families'][family]['remaining'], 5)
        self.assertFalse(result['replacement_card_effects_executed'])

    def test_exception_names_do_not_implicitly_change_custom_metadata(self):
        row = card(123, family='not-real-practice-writing')
        row['name'] = '练笔'
        result = replace_card(pool([row]), 123, [123], round_number=1, realm=1)
        self.assertEqual(result['card_id'], -1)

    def test_local_exception_cards_are_nonupgradeable_and_no_variant_ids_exist(self):
        rows = metadata_from_local([6000002, 7000109])
        self.assertTrue(all(row['no_upgrade'] for row in rows))
        for card_id in (6010002, 6020002, 7010109, 7020109):
            with self.subTest(card_id=card_id), self.assertRaises(ValueError):
                metadata_from_local([card_id])

    def test_upgrade_aliases_share_counts_and_cannot_duplicate_draw_weight(self):
        initial = pool([card(1, family='same'), card(10001, family='same')])
        result = draw_card(initial, [10001])
        self.assertEqual(len(initial['families']), 1)
        self.assertEqual(result['pool']['families']['same']['remaining'], 7)
        with self.assertRaises(ValueError):
            draw_card(initial, [1, 10001])

    def test_local_whitelist_preserves_alchemy_exceptions_and_distinguishes_namesake(self):
        rows = metadata_from_local([2000012, 2010012, 2000014, 2000015, 230, 6000002, 7000112])
        by_id = {row['card_id']: row for row in rows}
        for card_id in (2000012, 2010012, 2000014, 2000015):
            self.assertEqual(by_id[card_id]['copy_count'], 3)
        self.assertEqual(by_id[2000012]['family'], by_id[2010012]['family'])
        self.assertNotEqual(by_id[2000012]['family'], by_id[230]['family'])
        self.assertEqual(by_id[230]['copy_count'], 8)
        self.assertEqual(by_id[7000112]['copy_count'], 6)
        self.assertTrue(by_id[6000002]['replace_effect'])

    def test_contract_and_validation_do_not_claim_server_eligibility(self):
        initial = pool()
        self.assertFalse(contract(initial)['server_eligible_pool_verified'])
        self.assertFalse(contract(initial)['removal_timing_server_verified'])
        bad = deepcopy(initial)
        bad['families']['card-1']['remaining'] = 9
        with self.assertRaises(ValueError):
            snapshot(bad)
        with self.assertRaises(ValueError):
            draw_card(initial, [999])
        self.assertEqual(initial, pool())


if __name__ == '__main__':
    unittest.main()
