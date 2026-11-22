import copy
import unittest
from yixian.combat_start_context_bindings_v4 import bind_paper_opening
from yixian.full_battle_v45 import digest_json
from yixian.full_battle_v80 import _original_paper_binding, UnresolvedBattle


class PaperBindingTests(unittest.TestCase):
    def setUp(self):
        self.row = {'id': 'r', 'game_id': 'g', 'split': 'train', 'source_rules_version': '001.0008.0005',
            'round': 4, 'source': {'split': 'train', 'raw_sha256': 'a' * 64},
            'players': [{'candidate_start': {'board': [1, 2], 'xian_mo_strategies': v}} for v in ([16024], [])],
            'battle_params_evidence': {'entries': 1, 'sha256': digest_json([2])}, 'outcome': {'winner': 0}}
        self.ctx = {'game_id': 'g', 'source_raw_sha256': 'a' * 64, 'game_mode': 3, 'season_mec': 10,
                    'players': [{}, {}], 'battle_params': [2]}

    def test_original_binding_and_outcome_independence(self):
        original = copy.deepcopy(self.ctx); bound = bind_paper_opening(self.row, self.ctx)
        self.assertEqual(_original_paper_binding(self.row, bound)['stream'], [2])
        self.row['outcome'] = {'winner': 1, 'life': -999}
        self.assertEqual(bind_paper_opening(self.row, self.ctx), bound)
        self.assertEqual(self.ctx, original)

    def test_counterfactual_reuse_is_rejected(self):
        bound = bind_paper_opening(self.row, self.ctx)
        self.row['players'][0]['candidate_start']['board'] = [2, 1]
        with self.assertRaises(UnresolvedBattle): _original_paper_binding(self.row, bound)

    def test_full_stream_is_not_sliced_to_opening(self):
        self.ctx['battle_params'] = [1, 22, 0]
        self.row['battle_params_evidence'] = {'entries': 3, 'sha256': digest_json([1, 22, 0])}
        bound = bind_paper_opening(self.row, self.ctx)
        self.assertEqual(bound['battle_params'], [1, 22, 0])
        with self.assertRaisesRegex(UnresolvedBattle, 'other_parameter_consumers'):
            _original_paper_binding(self.row, bound)

    def test_mismatched_source_stream_or_replacement_rejected(self):
        original = copy.deepcopy(self.ctx)
        for key, value in [('source_raw_sha256', 'b' * 64), ('battle_params', [3]), ('battle_params', [True])]:
            self.ctx = copy.deepcopy(original); self.ctx[key] = value
            with self.assertRaises(ValueError): bind_paper_opening(self.row, self.ctx)
        self.ctx = bind_paper_opening(self.row, original)
        with self.assertRaises(ValueError): bind_paper_opening(self.row, self.ctx)


if __name__ == '__main__': unittest.main()
