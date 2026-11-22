import copy
import unittest
from yixian.combat_start_hand_projection_v3 import add_start_hands


class StartHandProjectionTests(unittest.TestCase):
    def setUp(self):
        self.source = {'split': 'train', 'raw_sha256': 'a' * 64, 'game_id': 'game'}
        self.row = {'id': 'r', 'game_id': 'game', 'split': 'train', 'source': self.source,
                    'round': 5, 'players': [{'snapshot_slot': s, 'candidate_start': {'board': [1, 2]}}
                                            for s in ('p1', 'p2')]}
        self.ctx = {'source_raw_sha256': 'a' * 64, 'game_id': 'game',
                    'scope': 'environment_calibration_only_not_policy_observation',
                    'players': [{'snapshot_slot': s, 'hand_count': 2} for s in ('p1', 'p2')]}
        self.turn = {'round': 5, **{s: {'publicData': {'lastRoundData': {'handCards': [7, 8], 'usedCards': [1, 2]},
                                'handCards': [999]}, 'privateData': {'handCards': [888]}}
                                for s in ('p1', 'p2')}, 'battleParams': [777], 'hpDelta': 123}
        self.req = [{'record_id': 'r', 'source_raw_sha256': 'a' * 64,
                     'player_index': 0, 'required_field': 'element_flag_hand'}]

    def project(self):
        return add_start_hands(self.turn, self.source, self.row, self.ctx, self.req)

    def test_only_selected_start_hand_added_and_order_preserved(self):
        before = copy.deepcopy((self.turn, self.row, self.ctx))
        result = self.project()
        hand = result['players'][0].pop('element_flag_hand')
        self.assertEqual(hand['raw_cards'], [7, 8])
        self.assertEqual(result, self.ctx)
        self.assertEqual((self.turn, self.row, self.ctx), before)
        self.assertIs(hand['environment_only'], True)
        self.assertIs(hand['policy_observation'], False)

    def test_current_private_and_outcomes_do_not_affect_projection(self):
        expected = self.project()
        self.turn['p1']['publicData']['handCards'] = [-1]
        self.turn['p1']['privateData'] = {'handCards': [90, 91, 92]}
        self.turn['battleParams'] = [0, 1]
        self.turn['hpDelta'] = -999
        self.row['outcome'] = {'winner_snapshot_slot': 'p2'}
        self.assertEqual(self.project(), expected)

    def test_missing_null_or_invalid_start_hand_never_falls_back(self):
        start = self.turn['p1']['publicData']['lastRoundData']
        for value in (None, [True, 8], ['7', 8], [7]):
            with self.subTest(value=value):
                start['handCards'] = value
                with self.assertRaises(ValueError): self.project()
        del start['handCards']
        with self.assertRaises(ValueError): self.project()

    def test_explicit_empty_hand_is_preserved(self):
        self.turn['p1']['publicData']['lastRoundData']['handCards'] = []
        self.ctx['players'][0]['hand_count'] = 0
        self.assertEqual(self.project()['players'][0]['element_flag_hand']['raw_cards'], [])

    def test_reject_stale_source_round_board_and_replacement(self):
        for key, replacement in [('record_id', 'other'), ('source_raw_sha256', 'b' * 64)]:
            original = self.req[0][key]; self.req[0][key] = replacement
            with self.assertRaises(ValueError): self.project()
            self.req[0][key] = original
        self.turn['round'] = 6
        with self.assertRaises(ValueError): self.project()
        self.turn['round'] = 5
        self.turn['p1']['publicData']['lastRoundData']['usedCards'] = [2, 1]
        with self.assertRaises(ValueError): self.project()
        self.turn['p1']['publicData']['lastRoundData']['usedCards'] = [1, 2]
        self.ctx['players'][0]['element_flag_hand'] = {}
        with self.assertRaises(ValueError): self.project()

    def test_reject_nontraining_and_other_context_fields(self):
        self.req[0]['required_field'] = 'sound_control_switch'
        with self.assertRaises(ValueError): self.project()
        self.req[0]['required_field'] = 'clouds_rain_hand'
        self.source['split'] = 'test'
        with self.assertRaises(ValueError): self.project()


if __name__ == '__main__': unittest.main()
