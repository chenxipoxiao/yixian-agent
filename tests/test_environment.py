"""Deck ordering is a curriculum; none of these tests establish live fidelity."""
from collections import Counter
from copy import deepcopy
import unittest

from yixian.environment import DeckOrderEnv, EnvironmentProtocolError


def battle_fixture():
    return {
        "seed": 1, "first_player": 0, "max_turns": 64,
        "players": [
            {"character": "sw1", "hp": 40, "max_hp": 40, "cultivation": 10,
             "round_number": 1, "cards": ["111011", "111011", "111021", "111031",
                                           "111041", "111051", "111061", "111071"]},
            {"character": "sw2", "hp": 40, "max_hp": 40, "cards": ["601011"] * 8},
        ],
    }


class DeckOrderTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.result = {"terminated": True, "truncated": False, "winner": 0}

        def simulator(battle):
            self.calls.append(deepcopy(battle))
            return deepcopy(self.result)

        self.simulator = simulator
        self.battle = battle_fixture()
        self.env = DeckOrderEnv(self.battle, simulator=simulator, shuffle_cards=False)

    def finish(self, env=None, order=range(8)):
        result = None
        for slot in order:
            result = (env or self.env).step(slot)
        return result

    def test_features_shape_mask_and_distinct_duplicate_slots(self):
        obs, info = self.env.reset(7)
        self.assertEqual(len(obs), 217)
        self.assertEqual(obs[64:72], [1.0] * 8)
        self.assertEqual(obs[72], 0.0)
        self.assertEqual(info["observation_schema"], "deck-order-v2-217")
        self.env.step(0)
        self.assertIn(1, self.env.legal_actions())  # Same card id, another owned copy.
        obs, reward, terminated, truncated, info = self.env.step(1)
        self.assertEqual(obs[0], 1.0)
        self.assertEqual(obs[9], 1.0)
        self.assertEqual(obs[64:66], [0.0, 0.0])
        self.assertEqual(info["selected_slots"], [0, 1])
        self.assertEqual((reward, terminated, truncated), (0.0, False, False))
        self.assertEqual(self.calls, [])

    def test_invalid_actions_do_not_advance_or_call_simulator(self):
        self.env.reset(7)
        self.env.step(2)
        before = self.env.observation()
        for action in (2, -1, 8, True, 0.0, "0", None):
            with self.subTest(action=action), self.assertRaises(ValueError):
                self.env.step(action)
            self.assertEqual(self.env.observation(), before)
        self.assertEqual(self.calls, [])

    def test_final_battle_is_exact_permutation_and_input_is_not_mutated(self):
        original = deepcopy(self.battle)
        self.env.reset(731)
        obs, reward, terminated, truncated, info = self.finish(order=reversed(range(8)))
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]["seed"], 731)
        self.assertEqual(self.calls[0]["players"][0]["cards"], self.battle["players"][0]["cards"][::-1])
        self.assertEqual(Counter(info["ordered_cards"]), Counter(self.battle["players"][0]["cards"]))
        self.assertEqual(self.calls[0]["players"][1], self.battle["players"][1])
        self.assertEqual(self.battle, original)
        self.assertEqual((reward, terminated, truncated), (1.0, True, False))
        self.assertTrue(info["label_usable"])
        self.assertEqual(obs[64:72], [0.0] * 8)
        self.assertEqual(self.env.legal_actions(), [])
        with self.assertRaises(ValueError):
            self.env.step(0)

    def test_true_loss_draw_and_truncation_rewards(self):
        cases = [(True, False, 1, -1.0, True), (True, False, None, 0.0, False),
                 (False, True, None, 0.0, False), (False, True, 0, 0.0, False)]
        for terminated, truncated, winner, reward, usable in cases:
            with self.subTest(terminated=terminated, truncated=truncated, winner=winner):
                self.result = {"terminated": terminated, "truncated": truncated, "winner": winner}
                self.env.reset(1)
                _, actual_reward, actual_term, actual_trunc, info = self.finish()
                self.assertEqual((actual_reward, actual_term, actual_trunc), (reward, terminated, truncated))
                self.assertEqual(info["label_usable"], usable)
                self.assertEqual(info["winner"], None if truncated else winner)

    def test_failed_final_simulation_is_retryable_without_advancing(self):
        self.env.reset(1)
        for slot in range(7):
            self.env.step(slot)
        before = self.env.observation()
        self.result = {"terminated": False, "truncated": False, "winner": None}
        with self.assertRaises(EnvironmentProtocolError):
            self.env.step(7)
        self.assertEqual(self.env.observation(), before)
        self.assertEqual(self.env.legal_actions(), [7])
        self.result = {"terminated": True, "truncated": False, "winner": 0}
        self.assertEqual(self.env.step(7)[1], 1.0)

    def test_simulator_exception_keeps_final_slot_legal(self):
        def fail(_):
            raise RuntimeError("fixture simulator failed")
        env = DeckOrderEnv(self.battle, simulator=fail)
        env.reset(1)
        for slot in range(7):
            env.step(slot)
        with self.assertRaisesRegex(RuntimeError, "fixture simulator failed"):
            env.step(7)
        self.assertEqual(env.legal_actions(), [7])

    def test_observation_never_encodes_opponent_hidden_state_or_seed(self):
        modified = deepcopy(self.battle)
        modified["players"][1].update(cards=["opponent-secret"] * 8, hp=999, character="hidden")
        other = DeckOrderEnv(modified, simulator=self.simulator, shuffle_cards=False)
        obs, _ = self.env.reset(1)
        other_obs, _ = other.reset(999999)
        self.assertEqual(obs, other_obs)
        for field, value in (("hp", 20), ("cards", ["changed-own-card"] * 8), ("character", "sw3")):
            changed = deepcopy(self.battle)
            changed["players"][0][field] = value
            candidate = DeckOrderEnv(changed, simulator=self.simulator, shuffle_cards=False)
            self.assertNotEqual(obs, candidate.reset(1)[0], field)

    def test_seed_replays_case_card_shuffle_and_episode(self):
        second = deepcopy(self.battle)
        second["players"][0]["cards"] = list(reversed(second["players"][0]["cards"]))
        pool = [{"id": "first", "battle": self.battle}, {"id": "second", "battle": second}]
        left, right = (DeckOrderEnv(pool, simulator=self.simulator) for _ in range(2))
        for seed in (1, 729, 1001):
            self.assertEqual(left.reset(seed), right.reset(seed))
            self.assertEqual(self.finish(left), self.finish(right))

    def test_contract_and_input_validation(self):
        contract = self.env.contract()
        self.assertFalse(contract["full_match_environment"])
        self.assertFalse(contract["current_season_verified"])
        self.assertEqual(contract["observation_dim"], 217)
        with self.assertRaises(RuntimeError):
            self.env.legal_actions()
        with self.assertRaises(ValueError):
            self.env.reset(True)
        bad = deepcopy(self.battle)
        bad["players"][0]["cards"].pop()
        with self.assertRaises(ValueError):
            DeckOrderEnv(bad)


if __name__ == "__main__":
    unittest.main()
