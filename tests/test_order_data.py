from collections import Counter
from copy import deepcopy
import unittest

import numpy as np

from yixian.order_data import (
    CHARACTER, VERSION, SCOPE, extract_boards, game_split,
    informative_steps, teacher_batch, validate_splits,
)
from yixian.replays import game_key


def replay():
    return {'data': {'gameId': 'order-test-game', 'version': VERSION,
        'seasonMec': 10, 'gameMode': 3, 'roundStats': [
            {'round': 5, 'p1': {'publicData': {'characterId': CHARACTER,
                'isAI': False, 'lastRoundData': {'usedCards': [1, 2, 1, 3],
                'hp': -9}}, 'privateData': {'hand': [999]}, 'result': 'win'}}]}}


class OrderDataTests(unittest.TestCase):
    def test_extracts_only_declared_human_character_and_version(self):
        source = replay()
        self.assertEqual(len(extract_boards(source, allowed_cards={1, 2, 3})), 1)
        for value in (True, None):
            changed = deepcopy(source)
            changed['data']['roundStats'][0]['p1']['publicData']['isAI'] = value
            self.assertEqual(extract_boards(changed, allowed_cards={1, 2, 3}), [])
        changed = deepcopy(source)
        changed['data']['version'] = 'old'
        self.assertEqual(extract_boards(changed, allowed_cards={1, 2, 3}), [])
        changed = deepcopy(source)
        changed['data']['roundStats'][0]['p1']['publicData']['characterId'] = 42
        self.assertEqual(extract_boards(changed, allowed_cards={1, 2, 3}), [])

    def test_filters_invalid_cards_and_previously_inspected_games(self):
        self.assertEqual(extract_boards(replay(), allowed_cards={1, 2}), [])
        self.assertEqual(extract_boards(replay(), allowed_cards={1, 2, 3},
            excluded_games={game_key('order-test-game')}), [])
        for board in ([1, 1, 1], [1, 2], [1, 2, True], [1, 2, 0]):
            changed = replay()
            changed['data']['roundStats'][0]['p1']['publicData']['lastRoundData']['usedCards'] = board
            self.assertEqual(extract_boards(changed, allowed_cards={1, 2, 3}), [])

    def test_views_have_same_dedup_id_and_no_private_or_outcome_features(self):
        source = replay()
        other = deepcopy(source)
        other['data']['roundStats'][0]['p2'] = other['data']['roundStats'][0].pop('p1')
        first = extract_boards(source, allowed_cards={1, 2, 3})[0]
        second = extract_boards(other, allowed_cards={1, 2, 3})[0]
        self.assertEqual(first['id'], second['id'])
        self.assertEqual(set(first), {'id', 'game_id', 'split', 'character_id',
            'board', 'first_observed_round', 'source_rules_version', 'season_mec',
            'scope', 'recorded_action_trajectory'})
        self.assertFalse(first['recorded_action_trajectory'])

    def test_all_boards_of_one_game_stay_together_and_tampering_rejected(self):
        first = extract_boards(replay(), allowed_cards={1, 2, 3})[0]
        other = replay()
        other['data']['roundStats'][0]['p1']['publicData']['lastRoundData']['usedCards'].reverse()
        second = extract_boards(other, allowed_cards={1, 2, 3})[0]
        summary = validate_splits([first, second])
        self.assertEqual(sum(summary['games'].values()), 1)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            validate_splits([first, first])
        second['split'] = 'test' if first['split'] != 'test' else 'train'
        with self.assertRaisesRegex(ValueError, 'split'):
            validate_splits([first, second])

    def test_teacher_observation_preserves_multiset_without_target_suffix(self):
        board = [1, 2, 1, 3, 4]
        batch = teacher_batch([board], np.random.default_rng(11), steps=[2])
        self.assertEqual(set(batch), {'candidates', 'prefix', 'available', 'targets'})
        self.assertEqual(batch['prefix'][0].tolist(), [1, 2, 0, 0, 0, 0, 0, 0])
        candidates, available = batch['candidates'][0], batch['available'][0]
        self.assertEqual(Counter(candidates[candidates != 0]), Counter(board))
        self.assertEqual(Counter(candidates[available]), Counter(board[2:]))
        self.assertFalse(np.any(batch['targets'] & ~batch['available']))
        np.testing.assert_array_equal(batch['targets'][0], available & (candidates == 1))

    def test_all_interchangeable_copies_are_targets(self):
        batch = teacher_batch([[1, 1, 2]], np.random.default_rng(1), steps=[0])
        self.assertEqual(int(batch['targets'].sum()), 2)
        self.assertEqual(int(batch['available'].sum()), 3)

    def test_deterministic_suffix_does_not_inflate_accuracy(self):
        self.assertEqual(informative_steps([1, 2, 2]), [0])
        for step in (1, 2, -1):
            with self.assertRaises(ValueError):
                teacher_batch([[1, 2, 2]], np.random.default_rng(1), steps=[step])

    def test_seed_reproduces_batches(self):
        boards = [[1, 2, 3], [2, 1, 2, 4]]
        first = teacher_batch(boards, np.random.default_rng(37))
        second = teacher_batch(boards, np.random.default_rng(37))
        for key in first:
            np.testing.assert_array_equal(first[key], second[key])


if __name__ == '__main__':
    unittest.main()
