from collections import Counter
import itertools
import unittest

import numpy as np

from yixian.order_evaluation import (decode_own_prefix, evaluate_orders, grouped_summary,
    position_counts, random_order_expectations, shuffled_candidates)


def ascending(candidates, prefix, available):
    return np.where(available, -candidates.astype(float), -np.inf)


class OrderEvaluationTests(unittest.TestCase):
    def test_prefix_is_previous_prediction_and_duplicate_copies_consumed(self):
        observed = []

        def scorer(candidates, prefix, available):
            observed.append(prefix[0].tolist())
            if not prefix.any():
                return np.where(available, candidates, -np.inf)
            self.assertEqual(prefix[0, 0], 3)
            return ascending(candidates, prefix, available)

        output = decode_own_prefix([[3, 1, 1, 2, 0, 0, 0, 0]], scorer)
        self.assertEqual(output, [[3, 1, 1, 2]])
        self.assertEqual(observed[2][:2], [3, 1])
        self.assertEqual(observed[3][:3], [3, 1, 1])

    def test_mixed_lengths_batching_preserves_every_occurrence(self):
        boards = [[1, 2, 1], [4, 2, 1, 4, 3, 2, 1, 3], [3, 2, 1, 2]]
        candidates = shuffled_candidates(boards, ['a', 'b', 'c'], 7)
        for batch_size in (1, 2, 8):
            self.assertEqual(decode_own_prefix(candidates, ascending, batch_size=batch_size),
                             [sorted(board) for board in boards])

    def test_illegal_or_nonfinite_policy_is_rejected_not_counted_as_legal(self):
        candidates = np.array([[1, 2, 3, 0, 0, 0, 0, 0]])
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            decode_own_prefix(candidates, lambda c, p, a: np.where(a, 0., 100.))
        with self.assertRaisesRegex(ValueError, 'non-finite'):
            decode_own_prefix(candidates, lambda c, p, a: np.full(c.shape, np.nan))

    def test_shuffle_is_stable_per_id_independent_of_batch_and_row_order(self):
        boards = [[1, 1, 2], [3, 2, 1, 2]]
        first = shuffled_candidates(boards, ['a', 'b'], 17)
        reversed_rows = shuffled_candidates(boards[::-1], ['b', 'a'], 17)
        np.testing.assert_array_equal(first, reversed_rows[::-1])
        for board, row in zip(boards, first):
            self.assertEqual(Counter(board), Counter(row[row > 0]))

    def test_random_duplicate_aware_expectation_matches_enumeration(self):
        board = [1, 1, 2, 3]
        permutations = list(itertools.permutations(board))
        expected_exact = sum(list(p) == board for p in permutations)/len(permutations)
        expected_positions = sum(sum(a == b for a, b in zip(p, board)) for p in permutations)/len(permutations)
        actual = random_order_expectations(board)
        self.assertAlmostEqual(actual[0], expected_exact)
        self.assertAlmostEqual(actual[1], expected_positions)

    def test_teacher_accuracy_and_full_board_accuracy_are_distinct(self):
        result, per_game = evaluate_orders([[2, 1, 3]], ['game'], ['board'], ascending,
            position_counts([[1, 2, 3]], 4), seed=7, batch_size=2, bootstrap_seed=8, bootstrap_samples=20)
        model = result['pooled_metrics']['model']
        self.assertEqual(model['teacher_next_card_accuracy'], .5)
        self.assertEqual(model['own_prefix_exact_board_accuracy'], 0)
        self.assertAlmostEqual(model['own_prefix_position_accuracy'], 1/3)
        self.assertEqual(result['illegal_predictions'], 0)
        self.assertEqual(per_game['game']['model'], model)
        self.assertFalse(result['game_strength_evaluated'])

    def test_uniform_model_nll_marginalizes_duplicates_like_random(self):
        def uniform(c, p, a):
            return np.where(a, 0., -np.inf)
        boards = [[1, 1, 2], [2, 1, 2, 3]]
        result, _ = evaluate_orders(boards, ['g1', 'g2'], ['b1', 'b2'], uniform,
            position_counts(boards, 4), seed=1, bootstrap_seed=2, bootstrap_samples=20)
        metrics = result['pooled_metrics']
        self.assertAlmostEqual(metrics['model']['teacher_nll'], metrics['random']['teacher_nll'])

    def test_intervals_resample_games_and_report_game_balanced_rates(self):
        groups = {}
        for game, boards, correct in (('large', 9, 1), ('small', 1, 0)):
            groups[game] = {}
            for policy in ('model', 'position_frequency', 'random'):
                success = correct if policy == 'model' else 0
                groups[game][policy] = Counter(boards=boards, decisions=boards, positions=3*boards,
                    nll=boards, correct=success*boards, exact=success*boards, positions_correct=success*3*boards)
        summary = grouped_summary(groups, bootstrap_seed=29, bootstrap_samples=200)
        self.assertAlmostEqual(summary['pooled_metrics']['model']['own_prefix_exact_board_accuracy'], .9)
        self.assertAlmostEqual(summary['game_macro_metrics']['model']['own_prefix_exact_board_accuracy'], .5)
        interval = summary['paired_game_macro_ci95']['random']['own_prefix_exact_board_accuracy']
        self.assertEqual(interval, {'model_minus_baseline': .5, 'low': 0., 'high': 1.})
        self.assertEqual(summary, grouped_summary(groups, bootstrap_seed=29, bootstrap_samples=200))

    def test_invalid_inputs_are_rejected_before_scoring(self):
        for boards, identifiers in (([[1, 2]], ['x']), ([[1, 1, 1]], ['x']),
                                   ([[1, 2, 3], [1, 2, 3]], ['same', 'same'])):
            with self.assertRaises(ValueError):
                shuffled_candidates(boards, identifiers, 3)


if __name__ == '__main__':
    unittest.main()
