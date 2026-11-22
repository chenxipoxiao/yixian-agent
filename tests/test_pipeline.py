import unittest

from yixian.pipeline import _seed_schedule, baseline_evaluate, paired_comparison


class FixedEnv:
    def reset(self, seed):
        self.seed = seed
        self.used = []
        return [], {'case_id': f'case-{seed % 2}'}

    def legal_actions(self):
        return [i for i in range(8) if i not in self.used]

    def step(self, action):
        if action not in self.legal_actions():
            raise AssertionError('Illegal baseline action')
        self.used.append(action)
        done = len(self.used) == 8
        return [], float(done), done, False, {'label_usable': self.seed != 1}


class PipelineTests(unittest.TestCase):
    def test_invalid_or_unresolved_results_do_not_improve_baseline(self):
        report = baseline_evaluate(FixedEnv(), [0, 1], 'random')
        self.assertEqual(report['completed'], 1)
        self.assertEqual(report['excluded'], 1)
        self.assertEqual(report['win_fraction'], 1)
        self.assertNotIn('reward', report['outcomes'][1])

    def test_pairing_requires_identical_fixtures_and_seeds(self):
        a = baseline_evaluate(FixedEnv(), [0, 1, 2])
        b = baseline_evaluate(FixedEnv(), [0, 1, 2], 'slot_order')
        result = paired_comparison(a, b)
        self.assertEqual(result['paired_episodes'], 2)
        self.assertEqual(result['excluded_pairs'], 1)
        self.assertEqual(result['mean_reward_delta'], 0)
        self.assertFalse(result['strength_claim'])
        b['outcomes'][0]['case_id'] = 'different-game'
        with self.assertRaises(ValueError):
            paired_comparison(a, b)

    def test_evaluation_schedules_cannot_overlap(self):
        with self.assertRaises(ValueError):
            _seed_schedule({'evaluation_episodes': 10, 'validation_seed_base': 20, 'test_seed_base': 25})
        with self.assertRaises(ValueError):
            _seed_schedule({'evaluation_episodes': 0, 'validation_seed_base': 20, 'test_seed_base': 30})


if __name__ == '__main__':
    unittest.main()
