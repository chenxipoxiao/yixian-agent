"""Tests of the pinned adapter, not claims of agreement with the live game."""
import copy
import json
from pathlib import Path
import unittest

from yixian.simulator import SimulatorError, engine_contract, is_available, simulate_battle


@unittest.skipUnless(is_available(), "Run python tools/setup_yisim.py to install the external reference")
class SimulatorTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / "examples" / "battle.json"
        self.battle = json.loads(path.read_text(encoding="utf-8"))

    def test_demo_finishes_and_keeps_input_unchanged(self):
        original = copy.deepcopy(self.battle)
        result = simulate_battle(self.battle)
        self.assertEqual(original, self.battle)
        self.assertTrue(result["terminated"])
        self.assertFalse(result["truncated"])
        self.assertEqual(result["winner"], 0)
        self.assertGreater(result["players"][0]["hp"], 0)
        self.assertLessEqual(result["players"][1]["hp"], 0)
        self.assertEqual(result["fidelity"], "legacy_unverified")
        self.assertFalse(result["current_season_verified"])

    def test_seeded_random_battle_is_repeatable_across_processes(self):
        for player in self.battle["players"]:
            player["cards"] = ["121081"] * 8  # Palm Thunder: seeded random damage.
            player["hp"] = player["max_hp"] = 80
        first = simulate_battle(self.battle)
        second = simulate_battle(self.battle)
        self.assertTrue(first["used_randomness"])
        self.assertEqual(first, second)

    def test_turn_limit_never_becomes_a_fake_win_or_destiny_loss(self):
        self.battle["max_turns"] = 1
        self.battle["include_log"] = True
        result = simulate_battle(self.battle)
        self.assertEqual(result["turns"], 1)
        self.assertFalse(result["terminated"])
        self.assertTrue(result["truncated"])
        self.assertIsNone(result["winner"])
        self.assertEqual(result["outcome"], "truncated")
        self.assertEqual([p["destiny"] for p in result["players"]], [100, 100])
        self.assertFalse(any(line.endswith(" wins") for line in result["log"]))

    def test_explicit_first_player_is_mapped_to_original_seat(self):
        for player in self.battle["players"]:
            player["cards"] = ["601011"] * 8
            player["hp"] = player["max_hp"] = 3
        self.battle["first_player"] = 1
        result = simulate_battle(self.battle)
        self.assertEqual(result["winner"], 1)
        self.assertEqual(result["turns"], 1)
        self.assertLessEqual(result["players"][0]["hp"], 0)
        self.assertEqual(result["players"][1]["hp"], 3)

    def test_unknown_card_is_rejected_instead_of_fuzzy_substitution(self):
        self.battle["players"][0]["cards"][0] = "999999999"
        with self.assertRaisesRegex(SimulatorError, "Unknown card id"):
            simulate_battle(self.battle)

    def test_missing_seed_and_unknown_player_field_are_rejected(self):
        del self.battle["seed"]
        with self.assertRaisesRegex(SimulatorError, "seed is required"):
            simulate_battle(self.battle)
        self.battle["seed"] = 1
        self.battle["players"][0]["invented_current_season_rule"] = 1
        with self.assertRaisesRegex(SimulatorError, "Unsupported player field"):
            simulate_battle(self.battle)

    def test_contract_does_not_claim_current_rules_or_full_match_support(self):
        contract = engine_contract()
        self.assertIsNone(contract["rules_version"])
        self.assertFalse(contract["rules_verified"])
        self.assertFalse(contract["full_match_environment"])


if __name__ == "__main__":
    unittest.main()
