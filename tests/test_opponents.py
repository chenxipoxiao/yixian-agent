from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from yixian.opponents import (
    assert_disjoint_games, build_opponent_library, load_fixtures,
    player_view, save_library, split_for_game_id,
)


class OpponentTests(unittest.TestCase):
    def setUp(self):
        self.contract = {"engine": "fixture-only", "rules_version": "test-rules", "revision": "1"}

    def record(self, game="game-1", view=0, **overrides):
        return {"id": f"{game}/view-{view}", "evidence": "synthetic",
                "source": {"game_id": game, "artifact": "unit-test-only"},
                "battle": {"players": [{"cards": ["a"]}, {"cards": ["b"]}]}, **overrides}

    def test_views_from_whole_games_remain_in_one_split(self):
        records = [self.record(f"game-{game}", view) for game in range(100) for view in range(8)]
        library = build_opponent_library(records, self.contract)
        by_game = {}
        for record in library["records"]:
            by_game.setdefault(record["source"]["game_id"], set()).add(record["split"])
        self.assertTrue(all(len(splits) == 1 for splits in by_game.values()))
        self.assertEqual(sum(map(len, library["games_by_split"].values())), 100)
        self.assertTrue(all(library["games_by_split"].values()))
        assert_disjoint_games(library["games_by_split"])

    def test_library_is_versioned_stably_and_copies_inputs(self):
        records = [self.record("a"), self.record("b")]
        library = build_opponent_library(records, self.contract)
        self.assertEqual(library, build_opponent_library(reversed(records), self.contract))
        changed = build_opponent_library(records, dict(self.contract, revision="2"))
        self.assertNotEqual(library["library_digest"], changed["library_digest"])
        records[0]["battle"]["players"][0]["cards"].append("mutated")
        self.assertEqual(library["records"][0]["battle"]["players"][0]["cards"], ["a"])

    def test_declared_split_cannot_override_whole_game_hash(self):
        expected = split_for_game_id("game-1")
        other = "test" if expected != "test" else "train"
        with self.assertRaisesRegex(ValueError, "whole-game"):
            build_opponent_library([self.record(split=other)], self.contract)
        with self.assertRaisesRegex(ValueError, "leakage"):
            assert_disjoint_games({"train": ["game-1"], "test": [" game-1 "]})

    def test_split_is_stable_under_whitespace_and_invalid_policy_rejected(self):
        self.assertEqual(split_for_game_id("game-1"), split_for_game_id(" game-1 "))
        for fractions in ((1, 1, 1), (1, -1, 1), (float("nan"), 0, 1)):
            with self.assertRaises(ValueError):
                split_for_game_id("game-1", fractions=fractions)

    def test_synthetic_provenance_never_becomes_verified_real_data(self):
        library = build_opponent_library([self.record()], self.contract)
        self.assertEqual(library["record_counts_by_evidence"], {"synthetic": 1, "real_game": 0})
        self.assertFalse(library["records"][0]["provenance_verified"])
        with self.assertRaisesRegex(ValueError, "provenance"):
            build_opponent_library([self.record(provenance_verified=True)], self.contract)

    def test_real_records_require_version_and_verified_provenance_needs_reference(self):
        record = self.record(evidence="real_game")
        with self.assertRaisesRegex(ValueError, "rules_version"):
            build_opponent_library([record], self.contract)
        record["source"]["rules_version"] = "old-rules"
        with self.assertRaisesRegex(ValueError, "version differs"):
            build_opponent_library([record], self.contract)
        record["source"]["rules_version"] = "test-rules"
        record["provenance_verified"] = True
        with self.assertRaisesRegex(ValueError, "verification artifact"):
            build_opponent_library([record], self.contract)
        record["source"]["verification_artifact"] = "audit.json"
        self.assertTrue(build_opponent_library([record], self.contract)["records"][0]["provenance_verified"])

    def test_same_game_cannot_mix_synthetic_and_real_views(self):
        real = self.record(view=1, evidence="real_game")
        real["source"]["rules_version"] = "test-rules"
        with self.assertRaisesRegex(ValueError, "Views from one game"):
            build_opponent_library([self.record(), real], self.contract)

    def test_duplicate_id_empty_library_and_bad_contract_rejected(self):
        for records in ([], [self.record(), self.record()], [self.record(engine_contract="wrong")]):
            with self.assertRaises(ValueError):
                build_opponent_library(records, self.contract)

    def state(self):
        return {"round_number": 6, "private": {"rng": 999}, "future_cards": ["future"],
                "players": [
                    {"character": "self", "cards": ["own-board"], "hand_cards": ["own-hand"],
                     "private": "private-self", "future_cards": ["future-self"]},
                    {"character": "opponent", "cards": ["hidden-board"], "hand_cards": ["hidden-hand"],
                     "private": "private-opponent", "future": "future-opponent"}],
                "public_observations": {"1": {"character": "opponent", "destiny": 50,
                     "last_seen_cards": ["old-public-board"], "observed_round": 5,
                     "cards": ["injected-hidden-board"], "hand_cards": ["injected-hand"],
                     "future": "injected-future"}}}

    def test_player_view_does_not_leak_hidden_or_future_state(self):
        state = self.state()
        view = player_view(state, 0)
        serialized = json.dumps(view)
        for secret in ("hidden-board", "hidden-hand", "private", "future", "injected", "999"):
            self.assertNotIn(secret, serialized)
        self.assertEqual(view["self"]["hand_cards"], ["own-hand"])
        self.assertEqual(view["opponents"][0]["last_seen_cards"], ["old-public-board"])
        view["self"]["cards"].append("mutated")
        self.assertEqual(state["players"][0]["cards"], ["own-board"])

    def test_no_explicit_public_observation_means_no_opponent_snapshot(self):
        state = self.state()
        state.pop("public_observations")
        self.assertEqual(player_view(state, 0)["opponents"], [{"seat": 1}])

    def test_future_or_untimed_boards_and_nested_field_injection_rejected(self):
        for edit in (lambda obs: obs.update(observed_round=7),
                     lambda obs: obs.pop("observed_round"),
                     lambda obs: obs.update(character={"secret": "nested"}),
                     lambda obs: obs.update(last_seen_cards=[{"secret": "nested"}])):
            state = self.state()
            edit(state["public_observations"]["1"])
            with self.assertRaises(ValueError):
                player_view(state, 0)

    def test_json_and_jsonl_input_and_saved_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixtures.json"
            path.write_text(json.dumps({"records": [self.record()]}), encoding="utf-8")
            self.assertEqual(load_fixtures(path), [self.record()])
            lines = path.with_suffix(".jsonl")
            lines.write_text(json.dumps(self.record()) + "\n", encoding="utf-8")
            self.assertEqual(load_fixtures(lines), [self.record()])
            library = build_opponent_library(load_fixtures(path), self.contract)
            output = Path(directory) / "library.json"
            save_library(library, output)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), library)
            tampered = deepcopy(library)
            tampered["records"][0]["split"] = "wrong"
            with self.assertRaisesRegex(ValueError, "digest"):
                save_library(tampered, output)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), library)


if __name__ == "__main__":
    unittest.main()
