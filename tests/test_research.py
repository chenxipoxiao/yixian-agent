import copy
import json
from pathlib import Path
import tempfile
import unittest

from yixian.research import (
    canonical_json, check_replays, compare_expected, contract_digest,
    load_jsonl, promotion_gate,
)


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.contract = {
            "engine": "fixture-only", "revision": "fixture-1",
            "rules_version": "test-rules", "rules_verified": True,
            "observation_schema": 1, "action_schema": 1,
        }
        self.record = {
            "id": "fixture-turn-1", "evidence": "real_game",
            "rules_version": "test-rules",
            "source": {"match_id": "fixture-match", "artifact": "unit-test-fixture"},
            "input": {"value": 7}, "expected": {"value": 7},
            "observed": {"value": 7, "extra": "allowed"},
        }

    def test_contract_hash_stable_but_sensitive_to_all_fields(self):
        reversed_contract = dict(reversed(list(self.contract.items())))
        self.assertEqual(contract_digest(self.contract), contract_digest(reversed_contract))
        changed = dict(self.contract, action_schema=2)
        self.assertNotEqual(contract_digest(self.contract), contract_digest(changed))
        self.assertNotEqual(contract_digest({"cards": [1, 2]}), contract_digest({"cards": [2, 1]}))

    def test_canonical_json_rejects_ambiguous_types(self):
        for value in (float("nan"), float("inf"), {1: "key"}, {"x": (1, 2)}):
            with self.assertRaises(ValueError):
                canonical_json(value)

    def test_jsonl_rejects_duplicate_keys_and_bad_line(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replays.jsonl"
            path.write_text('{"id":"a","id":"b"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                load_jsonl(path)
            path.write_text('{}\nnope\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, ":2:"):
                load_jsonl(path)

    def test_jsonl_loads_unicode_and_blank_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replays.jsonl"
            path.write_text('\ufeff\n' + json.dumps({"id": "回放"}) + '\n', encoding="utf-8")
            self.assertEqual(load_jsonl(path), [{"id": "回放"}])

    def test_deep_diff_distinguishes_missing_type_and_list_length(self):
        differences = compare_expected({"a": [1, 2], "b": True, "c": None}, {"a": [1], "b": 1})
        self.assertEqual({d.reason for d in differences}, {"length_mismatch", "type_mismatch", "missing_field"})
        self.assertEqual(compare_expected({"a": 1}, {"a": 1.0, "b": 2}), [])

    def test_real_evidence_and_self_checks_are_separate(self):
        synthetic = dict(self.record, id="self-check", evidence="simulator_self_check")
        report = check_replays([self.record, synthetic], contract=self.contract)
        self.assertEqual(report.real_game_matches, 1)
        self.assertEqual(report.simulator_self_checks, 1)
        self.assertEqual(report.real_source_match_ids, ("fixture-match",))
        self.assertEqual(report.failures, 0)

    def test_multiple_turns_do_not_inflate_real_match_count(self):
        second = dict(self.record, id="fixture-turn-2")
        report = check_replays([self.record, second], contract=self.contract)
        self.assertEqual(report.real_game_matches, 2)
        self.assertEqual(len(report.real_source_match_ids), 1)
        decision = promotion_gate(self.contract, replay_report=report, minimum_real_matches=2)
        self.assertIn("insufficient_real_game_matches", decision.blockers)

    def test_wrong_version_missing_source_empty_expected_and_duplicate_fail(self):
        records = [dict(self.record, rules_version="old"),
                   dict(self.record, id="no-source", source={}),
                   dict(self.record, id="empty", expected={}),
                   dict(self.record, id="empty")]
        report = check_replays(records, contract=self.contract)
        self.assertEqual(report.failures, 4)
        self.assertEqual(report.real_game_matches, 0)

    def test_unknown_contract_version_cannot_count_real_evidence(self):
        report = check_replays([self.record], contract=dict(self.contract, rules_version=None))
        self.assertEqual(report.real_game_matches, 0)
        self.assertEqual(report.failures, 1)

    def test_simulator_gets_copy_and_overrides_observed(self):
        original = copy.deepcopy(self.record)

        def simulator(state):
            state["value"] = 9
            return state

        report = check_replays([self.record], simulator, contract=self.contract)
        self.assertEqual(report.records[0].status, "mismatch")
        self.assertEqual(self.record, original)
        self.assertEqual(report.records[0].differences[0].path, "$.value")

    def test_simulator_error_is_failed_evidence(self):
        def simulator(_state):
            raise RuntimeError("missing card")

        report = check_replays([self.record], simulator, contract=self.contract)
        self.assertEqual(report.records[0].status, "simulator_error")
        self.assertEqual(report.failures, 1)

    def test_nonfinite_observed_is_not_evidence(self):
        record = dict(self.record, observed={"value": float("nan")})
        report = check_replays([record], contract=self.contract)
        self.assertEqual(report.failures, 1)

    def test_promotion_defaults_fail_closed(self):
        decision = promotion_gate({"engine": "unverified"})
        self.assertFalse(decision.ready)
        self.assertTrue({"rules_version_missing", "rules_not_verified", "tests_not_passed",
                         "full_match_environment_incomplete", "real_game_evidence_missing",
                         "candidate_contract_missing", "dataset_split_missing"} <= set(decision.blockers))

    def test_training_eval_overlap_and_contract_change_block_promotion(self):
        report = check_replays([self.record], contract=self.contract)
        decision = promotion_gate(
            dict(self.contract, revision="new"), tests_passed=True, full_match_environment=True,
            replay_report=report, training_ids=[" shared "], evaluation_ids=["shared"],
            candidate_contract_digest=contract_digest(self.contract),
        )
        self.assertTrue({"training_evaluation_overlap", "replay_contract_mismatch",
                         "candidate_contract_mismatch"} <= set(decision.blockers))

    def test_synthetic_only_cannot_pass_promotion(self):
        record = dict(self.record, evidence="simulator_self_check")
        report = check_replays([record], contract=self.contract)
        decision = promotion_gate(
            self.contract, tests_passed=True, full_match_environment=True,
            replay_report=report, training_ids=["train-match"], evaluation_ids=["eval-match"],
            candidate_contract_digest=contract_digest(self.contract),
        )
        self.assertEqual(decision.blockers, ("insufficient_real_game_matches",))

    def test_complete_structural_evidence_allows_offline_research_only(self):
        report = check_replays([self.record], contract=self.contract)
        decision = promotion_gate(
            self.contract, tests_passed=True, full_match_environment=True,
            replay_report=report, training_ids=["train-match"], evaluation_ids=["eval-match"],
            candidate_contract_digest=contract_digest(self.contract),
        )
        self.assertTrue(decision.ready)
        self.assertEqual(decision.scope, "offline_research_only")


if __name__ == "__main__":
    unittest.main()
