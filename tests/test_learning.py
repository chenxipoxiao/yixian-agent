import copy
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
    from yixian.learning import (PPOConfig, PolicyValueNet, masked_softmax, compute_gae,
                                 train, evaluate, load_checkpoint)
except ImportError:
    np = None


CONTRACT = {"engine": "test-bandit", "rules_version": "fixture-1",
            "observation_schema": "one-value", "action_schema": "two-actions"}


class Bandit:
    def __init__(self, truncate=False, unresolved=False):
        self.truncate = truncate
        self.unresolved = unresolved

    def reset(self, seed):
        self.done = False
        return [1.0], {"case_id": "unit-bandit"}

    def legal_actions(self):
        return [0, 1] if not self.done else []

    def step(self, action):
        if self.done or action not in (0, 1):
            raise ValueError("illegal")
        self.done = True
        info = {"label_usable": False} if self.unresolved else {}
        return [1.0], 1.0 if action == 1 else -1.0, not self.truncate, self.truncate, info


@unittest.skipIf(np is None, "Install requirements-training.txt for PPO tests")
class LearningTests(unittest.TestCase):
    def test_masked_softmax_exact_zero_and_single_action(self):
        p = masked_softmax([[1000, 1, -2], [5, 2000, 4]], [[False, True, True], [True, False, False]])
        self.assertEqual(p[0, 0], 0)
        np.testing.assert_allclose(p.sum(axis=1), 1)
        np.testing.assert_array_equal(p[1], [1, 0, 0])
        with self.assertRaises(ValueError):
            masked_softmax([[1, 2]], [[False, False]])

    def test_gae_resets_between_episodes_and_bootstraps_last_segment(self):
        adv, returns = compute_gae([0, 1, 2], [.5, .25, .75], [False, True, True], gamma=1, gae_lambda=1)
        np.testing.assert_allclose(returns, [1, 1, 2])
        np.testing.assert_allclose(adv, [.5, .75, 1.25])
        adv, returns = compute_gae([1], [.4], [False], gamma=.9, bootstrap_value=2)
        np.testing.assert_allclose(returns, [2.8])

    def test_ppo_backprop_finite_difference_with_clipped_and_masked_samples(self):
        model = PolicyValueNet(3, 3, 4, seed=7)
        config = PPOConfig(action_dim=3, clip_ratio=.2, entropy_coefficient=.07, value_coefficient=.4)
        x = np.array([[.1, -.2, .3], [1, .2, -.1], [.4, .5, -.1], [.5, -.7, .2]])
        masks = np.array([[True, True, False], [True, False, True], [True, True, True], [False, True, True]])
        actions = np.array([0, 2, 1, 2])
        probs, _, _ = model.forward(x, masks)
        selected = np.log(probs[np.arange(4), actions])
        batch = {"observations": x, "masks": masks, "actions": actions,
                 "old_log_probs": selected - np.log([1.4, .7, 1.1, .95]),
                 "advantages": np.array([.7, -.5, -.2, .3]),
                 "returns": np.array([1.2, -.4, .5, -.2])}
        _, grads, _ = model.loss_and_gradients(batch, config)
        epsilon = 1e-6
        for key, parameter in model.params.items():
            for index in np.ndindex(parameter.shape):
                original = parameter[index]
                parameter[index] = original + epsilon
                plus = model.loss_and_gradients(batch, config)[0]
                parameter[index] = original - epsilon
                minus = model.loss_and_gradients(batch, config)[0]
                parameter[index] = original
                self.assertAlmostEqual(grads[key][index], (plus - minus) / (2 * epsilon), places=6,
                                       msg=f"gradient {key}{index}")

    def test_learns_known_bandit_and_rejects_eval_seed_leakage(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.npz"
            config = PPOConfig(action_dim=2, hidden_size=8, updates=10, episodes_per_update=16,
                               learning_rate=.02, seed=11, minibatch_size=32,
                               reserved_evaluation_seeds=(30000, 30001))
            report = train(Bandit(), config, CONTRACT, path)
            self.assertEqual(report["episodes_trained"], 160)
            model = load_checkpoint(path, CONTRACT)
            probabilities, _, _ = model.forward([[1.0]], [[True, True]])
            self.assertGreater(probabilities[0, 1], .95)
            evaluation = evaluate(Bandit(), model, [30000, 30001], contract=CONTRACT)
            self.assertEqual(evaluation["mean_reward"], 1)
            with self.assertRaisesRegex(ValueError, "overlap"):
                evaluate(Bandit(), model, [10000], contract=CONTRACT)
            with self.assertRaisesRegex(ValueError, "contract mismatch"):
                load_checkpoint(path, dict(CONTRACT, action_schema="changed"))

    def test_checkpoint_resume_matches_uninterrupted_training(self):
        with tempfile.TemporaryDirectory() as directory:
            a, b = Path(directory) / "a.npz", Path(directory) / "b.npz"
            base = dict(action_dim=2, hidden_size=8, episodes_per_update=8, epochs=2, learning_rate=.003)
            train(Bandit(), PPOConfig(updates=4, **base), CONTRACT, a)
            train(Bandit(), PPOConfig(updates=2, **base), CONTRACT, b)
            train(Bandit(), PPOConfig(updates=2, **base), CONTRACT, b, resume=True)
            ma, mb = load_checkpoint(a, CONTRACT), load_checkpoint(b, CONTRACT)
            for key in ma.params:
                np.testing.assert_array_equal(ma.params[key], mb.params[key])
                np.testing.assert_array_equal(ma.optimizer["m"][key], mb.optimizer["m"][key])
                np.testing.assert_array_equal(ma.optimizer["v"][key], mb.optimizer["v"][key])
            self.assertEqual(ma.training_state, mb.training_state)
            with self.assertRaisesRegex(ValueError, "hyperparameters"):
                train(Bandit(), PPOConfig(updates=1, **dict(base, learning_rate=.004)), CONTRACT, b, resume=True)

    def test_truncated_episodes_never_update_model(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.npz"
            config = PPOConfig(action_dim=2, hidden_size=8, updates=2, episodes_per_update=3, seed=5)
            report = train(Bandit(truncate=True), config, CONTRACT, path)
            self.assertEqual(report["episodes_trained"], 0)
            self.assertEqual(report["episodes_excluded"], 6)
            model = load_checkpoint(path, CONTRACT)
            initial = PolicyValueNet(1, 2, 8, seed=5)
            for key in model.params:
                np.testing.assert_array_equal(model.params[key], initial.params[key])
            evaluation = evaluate(Bandit(True), model, [30000], contract=CONTRACT)
            self.assertIsNone(evaluation["mean_reward"])
            self.assertIsNone(evaluation["win_fraction"])
            self.assertEqual(evaluation["outcomes"][0]["case_id"], "unit-bandit")
            self.assertEqual(evaluation["outcomes"][0]["status"], "truncated")

    def test_reserved_eval_seed_collision_fails_before_training(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.npz"
            config = PPOConfig(action_dim=2, updates=1, episodes_per_update=2,
                               reserved_evaluation_seeds=(10001,))
            with self.assertRaisesRegex(ValueError, "overlaps"):
                train(Bandit(), config, CONTRACT, path)
            self.assertFalse(path.exists())

    def test_unresolved_terminal_labels_never_train_or_count_as_draws(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.npz"
            config = PPOConfig(action_dim=2, hidden_size=8, updates=1, episodes_per_update=2)
            report = train(Bandit(unresolved=True), config, CONTRACT, path)
            self.assertEqual(report["episodes_trained"], 0)
            self.assertEqual(report["episodes_excluded"], 2)
            model = load_checkpoint(path, CONTRACT)
            initial = PolicyValueNet(1, 2, 8)
            for key in model.params:
                np.testing.assert_array_equal(model.params[key], initial.params[key])
            evaluation = evaluate(Bandit(unresolved=True), model, [30000], contract=CONTRACT)
            self.assertEqual(evaluation["excluded"], 1)
            self.assertEqual(evaluation["outcomes"][0]["status"], "unresolved_outcome")
            self.assertIsNone(evaluation["win_fraction"])
            self.assertIsNone(evaluation["mean_reward"])
            with self.assertRaisesRegex(ValueError, "max_episode_steps"):
                evaluate(Bandit(), model, [30000], contract=CONTRACT, max_episode_steps=0)


if __name__ == '__main__':
    unittest.main()
