import copy
import unittest

from yixian.tactical_information import (information_set, sealed_decisions,
    match_replay_contexts, replay_continuation_gate)
from yixian.tactical_rules import TacticalCatalogue, card_features, effect_key, FEATURE_DIM
from yixian.tactical_search import Scenario, search_lineups, unique_orders


def table():
    return {'schema': 'explicit-seat-visibility-v1', 'round_number': 3, 'rules_fingerprint': 'rules-a',
            'seats': [{'seat': i, 'public': {'character': 1000003+i, 'career': i, 'destiny': 90,
                                         'handCards': [999], 'next_board': [999]},
                       'private': {'hand': [i+1], 'board': [1, 2], 'rerolls': 3},
                       'revealed_boards': [{'round': 1, 'board': [1, 2], 'private_hand': [999]}]}
                      for i in range(8)]}


class RuleFeaturesTests(unittest.TestCase):
    def test_numeric_patch_reaches_every_route_without_changing_template(self):
        row = {'id': 1, 'attack': 3, 'otherParams': [2], 'desc': '{attack}攻'}
        new = dict(row, attack=4)
        self.assertNotEqual(card_features(row), card_features(new))
        self.assertEqual(effect_key(row), effect_key(new))
        before = TacticalCatalogue([row], rules_version='a', source_sha256='a')
        after = TacticalCatalogue([new], rules_version='b', source_sha256='b')
        for role in ('transition', 'target', 'counters'):
            a = before.describe_route(transition=[1], target=[1], counters=[1])[role]
            b = after.describe_route(transition=[1], target=[1], counters=[1])[role]
            self.assertNotEqual(a, b)
        self.assertNotEqual(before.fingerprint, after.fingerprint)

    def test_missing_zero_padding_and_parameter_order_are_distinct(self):
        self.assertNotEqual(card_features({}), card_features({'attack': 0}))
        self.assertNotEqual(card_features({'otherParams': [1, 2]}), card_features({'otherParams': [2, 1]}))
        cat = TacticalCatalogue([{'id': 1}], rules_version='a', source_sha256='a')
        self.assertEqual(cat.matrix([1])[0], [0.]*FEATURE_DIM)
        with self.assertRaises(ValueError): cat.matrix([2])
        with self.assertRaises(ValueError): card_features({'attack': float('nan')})
        with self.assertRaises(ValueError): card_features({'otherParams': [0]*9})


class InformationTests(unittest.TestCase):
    def test_opponent_hidden_state_and_future_result_do_not_affect_input(self):
        state = table(); first = information_set(state, 0)
        for seat in state['seats'][1:]:
            seat['private'] = {'hand': [555555], 'board': [666666]}
            seat['winner_next_round'] = True
        state['rng_state'] = 99
        self.assertEqual(first, information_set(state, 0))
        self.assertNotIn('handCards', first['players'][1]['public'])
        self.assertNotIn('private_hand', first['players'][1]['history'][0])
        state['seats'][0]['private']['hand'] = [8]
        self.assertNotEqual(first['digest'], information_set(state, 0)['digest'])
        state['seats'][1]['public']['fates'] = [27]
        self.assertEqual(information_set(state, 0)['players'][1]['public']['fates'], [27])

    def test_history_current_future_duplicates_and_raw_replay_rejected(self):
        for round_number in (3, 4, 0):
            state = table(); state['seats'][1]['revealed_boards'][0]['round'] = round_number
            with self.assertRaises(ValueError): information_set(state, 0)
        state = table(); state['seats'][0]['revealed_boards'] *= 2
        with self.assertRaises(ValueError): information_set(state, 0)
        with self.assertRaises(ValueError): information_set({'publicData': {}}, 0)

    def test_sealed_actions_and_mutation_isolation(self):
        state = table(); before = copy.deepcopy(state); seen = []
        def policy(view, options):
            seen.append(copy.deepcopy(view)); view['own']['hand'].append(123); options[0]['extra'] = True
            return 'a'
        options = {i: [{'id': 'a'}] for i in range(8)}
        result = sealed_decisions(state, {i: policy for i in range(8)}, options)
        self.assertEqual(state, before); self.assertEqual(len(seen), 8)
        self.assertNotIn('extra', result['actions'][0]); self.assertNotIn('actions', seen[-1])
        with self.assertRaises(ValueError):
            sealed_decisions(state, {i: lambda *_: 'illegal' for i in range(8)}, options)

    def test_match_uses_same_career_only_known_before_cutoff(self):
        context = {'game_id': 'g', 'context_id': 'c', 'split': 'train', 'rules_fingerprint': 'a',
                   'cutoff_round': 2, 'public_players': [{'character': 3, 'career': 2,
                   'career_known_by_round': 2, 'revealed_core': [1, 2]}], 'final_rank': 1}
        kwargs = dict(character=3, career=2, round_number=3, rules_fingerprint='a', split='train', public_core=[2])
        result = match_replay_contexts([context], **kwargs)
        self.assertEqual(result[0]['public_core_overlap'], 1)
        context['final_rank'] = 8; self.assertEqual(result, match_replay_contexts([context], **kwargs))
        context['public_players'][0]['career_known_by_round'] = 3
        self.assertEqual([], match_replay_contexts([context], **kwargs))
        with self.assertRaises(ValueError): match_replay_contexts([context], **dict(kwargs, split='test'))
        self.assertFalse(replay_continuation_gate(tactical_action_changed=True)['can_import_future_recorded_state'])
        self.assertFalse(replay_continuation_gate(tactical_action_changed=False)['can_import_future_recorded_state'])


class SearchTests(unittest.TestCase):
    def run_search(self, matrix, *, risk=0., cap=20, broken=None):
        view = {'digest': 'v', 'rules_fingerprint': 'r'}
        scenarios = [Scenario(str(i), .5, {'index': i}, 'v', 'r', 'software_fixture') for i in range(2)]
        def evaluate(board, scenario):
            value = matrix[tuple(board)][scenario['index']]
            return {'utility': value, 'resolved': broken != (tuple(board), scenario['index']),
                    'terminated': True, 'truncated': False, 'rules_fingerprint': 'r'}
        return search_lineups(view, [1, 2], [(1, 2), (2, 1)], scenarios, evaluate,
                              risk_weight=risk, max_evaluations=cap)

    def test_selects_one_board_across_hidden_states_not_clairvoyant_best(self):
        result = self.run_search({(1, 2): [10, -10], (2, 1): [2, 2]})
        self.assertEqual(result['selected_board'], [2, 1])
        self.assertEqual(result['candidates'][0]['expected_utility'], 0)
        self.assertFalse(result['training_label_allowed'])

    def test_risk_changes_choice_without_changing_scenarios(self):
        matrix = {(1, 2): [10, -2], (2, 1): [3, 3]}
        self.assertEqual(self.run_search(matrix)['selected_board'], [1, 2])
        self.assertEqual(self.run_search(matrix, risk=1)['selected_board'], [2, 1])

    def test_unresolved_never_dropped_or_renormalized(self):
        result = self.run_search({(1, 2): [10, -10], (2, 1): [1, 1]}, broken=((1, 2), 1))
        self.assertEqual(result['selected_board'], [2, 1])
        self.assertFalse(result['candidates'][0]['eligible'])

    def test_budget_keeps_complete_scenario_sets_and_duplicates_unique(self):
        result = self.run_search({(1, 2): [1, 1], (2, 1): [2, 2]}, cap=3)
        self.assertEqual(result['evaluations'], 2); self.assertTrue(result['budget_exhausted'])
        self.assertEqual(len(list(unique_orders([1, 1, 2], 20))), 3)
        self.assertEqual(len(list(unique_orders([1, 2, 3], 2))), 2)

    def test_invalid_proposal_stale_prior_and_truncated_results_fail_closed(self):
        view = {'digest': 'v', 'rules_fingerprint': 'r'}
        scenario = Scenario('a', 1., {}, 'v', 'r', 'hypothesis')
        with self.assertRaises(ValueError): search_lineups(view, [1, 2], [[2, 2]], [scenario], lambda *_: {})
        with self.assertRaises(ValueError):
            search_lineups(view, [1, 2], [[1, 2]], [Scenario('a', 1., {}, 'future', 'r', 'hypothesis')], lambda *_: {})
        result = search_lineups(view, [1, 2], [[1, 2]], [scenario], lambda *_:
            {'utility': 100, 'resolved': True, 'terminated': False, 'truncated': True, 'rules_fingerprint': 'r'})
        self.assertIsNone(result['selected_board'])
