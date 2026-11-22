from copy import deepcopy
import json
import unittest

from yixian.card_pool import create_pool
from yixian.fate_acquisition import (grant_acquired_fate_cards, import_fate_acquisition_state,
    unacknowledged_grant_fates, LEDGER, UnknownAcquisitionState, contract)
from yixian.fate_catalog import discover_runtime_support
from yixian.effects import EffectEngine, SUPPORTED_FATES
from yixian.match_flow import FlowRules, run_match


def catalog():
    return {card: {'id': card, 'owner': 1000003, 'level': realm, 'rarity': 0,
                   'hidden': True, 'obsolete': False} for card, realm in ((15, 4), (16, 5))}


def actor(fates=None):
    return {'id': 'agent', 'character_id': 1000003, 'fates': [85, 86] if fates is None else fates,
            'life': 100, 'exp': 55, 'cards': [101], 'hand_cards': [], 'rerolls': 3,
            'card_pool': create_pool([], seed=85)}


def grant(player, fates=(85, 86), metadata=None):
    return grant_acquired_fate_cards(player, fates, catalog() if metadata is None else metadata, source_ref='test-selection')


class AcquisitionTests(unittest.TestCase):
    def test_existing_pool_exhaustion_card_does_not_block_an_independent_grant(self):
        player = actor(); player['hand_cards'] = [-1]
        result = grant(player, (85,))
        self.assertEqual(result['player']['hand_cards'], [-1, 15])
        self.assertEqual(result['player']['card_pool'], player['card_pool'])

    def test_two_new_fates_add_base_cards_without_pool_or_resource_change(self):
        player = actor(); before = deepcopy(player)
        result = grant(player)
        self.assertEqual(result['player']['hand_cards'], [15, 16])
        for key in ('cards', 'exp', 'life', 'rerolls', 'card_pool'):
            self.assertEqual(result['player'][key], before[key])
        self.assertEqual([e['pool_delta'] for e in result['events']], [0, 0])
        self.assertEqual(player, before)

    def test_retry_after_card_leaves_hand_does_not_regrant(self):
        player = grant(actor())['player']; player['hand_cards'] = []
        player = json.loads(json.dumps(player))
        retry = grant(player)
        self.assertEqual(retry['player']['hand_cards'], [])
        self.assertEqual(retry['events'], [])
        imported = import_fate_acquisition_state(player, source_ref='later-snapshot')
        self.assertEqual(imported['player'], player)
        self.assertEqual(imported['events'], [])

    def test_imported_ownership_never_generates_a_missing_card(self):
        player = actor(); player.pop('hand_cards')
        first = import_fate_acquisition_state(player, source_ref='recorded-round-8')
        self.assertNotIn('hand_cards', first['player'])
        self.assertEqual([e['cards_generated'] for e in first['events']], [0, 0])
        self.assertFalse(any(e['reward_delivery_verified'] for e in first['events']))
        second = grant(first['player'])
        self.assertEqual(second['events'], [])
        self.assertNotIn('hand_cards', second['player'])
        self.assertEqual(second['player']['effect_state'][LEDGER]['85']['origin'], 'imported_snapshot')

    def test_each_fate_has_an_independent_receipt(self):
        first = grant(actor(), (85,))['player']
        second = grant(first, (86,))
        self.assertEqual(second['player']['hand_cards'], [15, 16])
        self.assertEqual([e['effect_id'] for e in second['events']], [86])

    def test_overfull_hand_does_not_convert_or_merge_the_grant(self):
        player = actor(); player['hand_cards'] = [15] * 14
        result = grant(player, (85,))
        self.assertEqual(result['player']['hand_cards'], [15] * 15)
        self.assertEqual(result['player']['exp'], 55)
        self.assertEqual(result['player']['cards'], [101])

    def test_invalid_batch_is_atomic(self):
        player = actor(); before = deepcopy(player); cards = catalog(); cards.pop(16)
        with self.assertRaises(UnknownAcquisitionState): grant(player, metadata=cards)
        self.assertEqual(player, before)

    def test_metadata_cannot_change_card_owner_level_or_rarity(self):
        for field, value in [('id', 10015), ('owner', 99), ('rarity', 1), ('level', 3), ('hidden', False), ('obsolete', True)]:
            cards = catalog(); cards[15][field] = value
            with self.assertRaises(UnknownAcquisitionState): grant(actor(), (85,), cards)

    def test_explicit_valid_hand_and_owned_fate_required(self):
        for hand in (None, [0], ['15'], [True]):
            player = actor(); player['hand_cards'] = hand
            with self.assertRaises(UnknownAcquisitionState): grant(player, (85,))
        for fates in ([85, 85], [27], [True]):
            with self.assertRaises(ValueError): grant(actor(), fates)
        with self.assertRaises(ValueError): grant(actor([]), (85,))

    def test_other_character_and_mirror_are_not_assumed_supported(self):
        for field, value in [('character_id', 3), ('is_mirror', True), ('is_mirror', None)]:
            player = actor(); player[field] = value
            with self.assertRaises(UnknownAcquisitionState): grant(player)
            with self.assertRaises(UnknownAcquisitionState): import_fate_acquisition_state(player, source_ref='r1')

    def test_corrupt_receipt_does_not_reset_into_fresh_grant(self):
        player = grant(actor())['player']
        player['effect_state'][LEDGER]['85']['card_id'] = 16
        with self.assertRaises(ValueError): grant(player)

    def test_import_detection_and_partial_coverage_do_not_admit_battle_labels(self):
        player = import_fate_acquisition_state(actor([85]), source_ref='r1')['player']
        self.assertEqual(unacknowledged_grant_fates(player, [85, 86]), [86])
        support = discover_runtime_support()
        self.assertEqual(support['partial_regular'][85], ['acquisition_card_grant'])
        self.assertNotIn(85, SUPPORTED_FATES)
        self.assertFalse(contract()['candidate_eligibility_implemented'])
        self.assertFalse(contract()['current_server_rules_verified'])


def opponents():
    return [{'id': f'opponent-{i}', 'rounds': {r: {'cards': [101], 'character_id': 1000003,
            'fates': [], 'talent_counters': {}, 'exp': 5, 'hand_cards': []} for r in (1, 2)}} for i in range(7)]


def flow(**kwargs):
    values = dict(rules=FlowRules(max_rounds=2), self_character_id=1000003, self_cards=[101],
                  effect_engine=EffectEngine(), fate_acquisition_card_catalog=catalog(), resolver=lambda *args: {'winner': None})
    values.update(kwargs)
    fixtures = values.pop('opponents', opponents())
    return run_match(fixtures, **values)


class AcquisitionFlowTests(unittest.TestCase):
    def test_initial_fresh_fate_grants_once_without_automatic_board_placement(self):
        result = flow(self_fates=[85])
        self.assertEqual(result['players'][0]['hand_cards'], [15])
        self.assertEqual(result['players'][0]['cards'], [101])
        grants = [x for e in result['journal'] if e['phase'] == 'fate_acquisition_effects' for x in e['effects']]
        self.assertEqual(len(grants), 1)
        self.assertFalse(result['policy_training_allowed'])

    def test_actual_choice_hook_grants_at_two_distinct_ascensions(self):
        result = flow(rules=FlowRules(initial_exp=55, max_rounds=1),
                      normal_fate_offers={2: [25], 3: [27], 4: [85], 5: [86]})
        self.assertEqual(result['players'][0]['hand_cards'], [15, 16])
        choices = [e for e in result['journal'] if e['phase'] == 'choose_fate' and e['selected'] in (85, 86)]
        self.assertEqual([e['level'] for e in choices], [4, 5])
        self.assertTrue(all(e['effects_applied'] for e in choices))

    def test_snapshot_refresh_imports_hand_but_never_repeats_grant(self):
        fixtures = opponents()
        fixtures[0]['rounds'][1].update(fates=[85], hand_cards=[15])
        fixtures[0]['rounds'][2].update(fates=[85, 86], hand_cards=[16])
        original = deepcopy(fixtures)
        result = flow(opponents=fixtures)
        player = result['players'][1]
        self.assertEqual(player['hand_cards'], [16])
        self.assertEqual(set(player['effect_state'][LEDGER]), {'85', '86'})
        self.assertTrue(all(r['origin'] == 'imported_snapshot' for r in player['effect_state'][LEDGER].values()))
        imports = [x for e in result['journal'] if e['phase'] == 'fate_acquisition_import' for x in e['effects']]
        self.assertEqual(len(imports), 2)
        self.assertEqual(fixtures, original)

    def test_overflow_is_counted_only_at_the_next_round_draw_boundary(self):
        result = flow(self_fates=[85], draw_cards_by_round={1: [101] * 12})
        self.assertEqual(len(result['players'][0]['hand_cards']), 13)
        self.assertEqual(result['players'][0]['exp'], 5)
        overflow = [e for e in result['journal'] if e['phase'] == 'cultivation_change' and e['reason'] == 'overfull_hand_missed_draws']
        self.assertEqual([e['delta'] for e in overflow], [1])
        remaining = [e for e in result['journal'] if e['phase']=='round_draws' and e['round']==2][0]
        self.assertEqual(remaining['plan']['actual_draw_count'],2)
        self.assertFalse(remaining['normal_draws_generated'])

    def test_counterfactual_hand_blocks_new_replay_acquisition(self):
        fixtures = opponents()
        for state in fixtures[0]['rounds'].values(): state.update(fates=[65], talent_counters={'65': 1})
        fixtures[0]['rounds'][2].update(fates=[65, 85], hand_cards=[15])
        def resolver(left, right, *args):
            if 'opponent-0' not in (left['id'], right['id']): return {'winner': None}
            return {'winner': 1 if left['id'] == 'opponent-0' else 0, 'life_damage': 100}
        result = flow(opponents=fixtures, resolver=resolver)
        self.assertEqual(result['players'][1]['hand_cards'], [12])
        self.assertEqual(result['players'][1]['life'], 1)
        self.assertNotIn('85', result['players'][1]['effect_state'][LEDGER])
        self.assertEqual(result['fully_completed_rounds'], 1)
        self.assertEqual(result['unresolved_effect_actions'][0]['kind'], 'counterfactual_acquisition_continuation_required')

    def test_new_card_in_hand_is_not_a_dragon_scale_board_candidate(self):
        from test_dragon_scale_reward import catalog as upgrade_catalog
        def lose(left, right, *args):
            if 'agent' not in (left['id'], right['id']): return {'winner': None}
            return {'winner': 1 if left['id'] == 'agent' else 0, 'life_damage': 30}
        result = flow(self_fates=[27, 85], rules=FlowRules(initial_life=40, max_rounds=1),
                      post_battle_card_catalog=upgrade_catalog(), resolver=lose)
        self.assertEqual(result['players'][0]['cards'], [10101])
        self.assertEqual(result['players'][0]['hand_cards'], [15])

    def test_opt_in_requires_engine_and_leaves_default_flow_unchanged(self):
        with self.assertRaises(ValueError): flow(effect_engine=None)
        result = flow(self_fates=[85], fate_acquisition_card_catalog=None)
        self.assertFalse(result['fate_acquisition_enabled'])
        self.assertEqual(result['players'][0]['hand_cards'], [])
