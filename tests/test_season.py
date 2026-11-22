"""Tests use explicit fixture candidates, never an invented live-game sampler."""
import unittest

from yixian.season import SeasonAction, SeasonCatalog, SeasonDecision, UnknownSeasonRule


def catalog_fixture():
    npcs = [
        {"id": 1, "specialSkip": 24, "isSinglePendingNpc": False},
        {"id": 24, "specialSkip": 24, "isSinglePendingNpc": False},
        {"id": 25, "specialSkip": 25, "isSinglePendingNpc": False},
        {"id": 26, "specialSkip": 25, "isSinglePendingNpc": True},
        {"id": 2, "specialSkip": 999, "isSinglePendingNpc": False},
    ]
    strategies = [
        {"id": 1001, "npc": 1, "isAvailable": True},
        {"id": 1002, "npc": 1, "isAvailable": True, "_unknown_fields": ["fixture-expression"]},
        {"id": 1003, "npc": 1, "isAvailable": False},
        {"id": 24001, "npc": 24, "isAvailable": True},
        {"id": 24002, "npc": 24, "isAvailable": True},
        {"id": 25001, "npc": 25, "isAvailable": True},
        {"id": 26001, "npc": 26, "isAvailable": True},
        {"id": 26002, "npc": 26, "isAvailable": True},
        {"id": 2001, "npc": 2, "isAvailable": True},
    ]
    return SeasonCatalog(npcs, strategies, evidence={"fixture_only": True})


class SeasonDecisionTests(unittest.TestCase):
    def setUp(self):
        self.catalog = catalog_fixture()
        self.decision = SeasonDecision(self.catalog)
        # This sentinel is fixture-only; production must supply the observed ID.
        self.skip_id = -100

    def begin_normal(self, offer_id="round-fixture"):
        return self.decision.begin_offer(offer_id, 1, [1001, 1002, self.skip_id],
                                         skip_strategy_id=self.skip_id)

    def test_only_supplied_candidates_are_legal(self):
        self.begin_normal()
        self.assertEqual(self.decision.legal_actions(), [SeasonAction("select", 1001),
                         SeasonAction("select", 1002), SeasonAction("skip", self.skip_id)])
        before = self.decision.snapshot()
        for action in (SeasonAction("select", 1003), SeasonAction("skip", 1001),
                       SeasonAction("select", True), {"kind": "select", "strategy_id": 999},
                       {"kind": "select", "strategy_id": 1001, "fake": True}):
            with self.subTest(action=action), self.assertRaises(ValueError):
                self.decision.step(action)
            self.assertEqual(self.decision.snapshot(), before)

    def test_selection_is_request_receipt_without_fake_effects(self):
        self.begin_normal()
        receipt = self.decision.step({"kind": "select", "strategy_id": 1002})
        self.assertEqual(receipt["request_type"], "SelectXianMoStrategyReq")
        self.assertFalse(receipt["effects_applied"])
        self.assertFalse(receipt["server_acknowledged"])
        self.assertTrue(any("not yet decoded" in gap for gap in receipt["rule_gaps"]))
        self.assertEqual(self.decision.legal_actions(), [])
        with self.assertRaises(ValueError):
            self.decision.step(SeasonAction("select", 1001))
        with self.assertRaises(ValueError):
            self.begin_normal()  # Reusing a consumed request ID would double-apply intent.

    def test_first_skip_waits_for_external_followup_then_second_skip_does_not(self):
        self.begin_normal()
        receipt = self.decision.step(SeasonAction("skip", self.skip_id))
        self.assertTrue(receipt["first_skip_used"])
        self.assertEqual(receipt["awaiting_suanni_pool"], 24)
        self.assertEqual(self.decision.legal_actions(), [])
        before = self.decision.snapshot()
        with self.assertRaises(ValueError):
            self.begin_normal("too-early")
        self.assertEqual(self.decision.snapshot(), before)
        self.decision.begin_offer("helper", 24, [24001, 24002], suanni_offer=True)
        self.decision.step(SeasonAction("select", 24002))
        self.assertIsNone(self.decision.snapshot()["awaiting_suanni_pool"])
        self.begin_normal("next-npc")
        receipt = self.decision.step(SeasonAction("skip", self.skip_id))
        self.assertTrue(receipt["first_skip_used"])
        self.assertIsNone(receipt["awaiting_suanni_pool"])

    def test_shared_pool_locks_one_fate_and_uses_configured_followup(self):
        before = self.decision.snapshot()
        with self.assertRaisesRegex(ValueError, "shared fate pool"):
            self.decision.begin_offer("shared", 26, [26001, 26002])
        self.assertEqual(self.decision.snapshot(), before)
        self.decision.begin_offer("shared", 26, [26001, self.skip_id], skip_strategy_id=self.skip_id)
        receipt = self.decision.step(SeasonAction("skip", self.skip_id))
        self.assertTrue(receipt["shared_pool"])
        self.assertEqual(receipt["awaiting_suanni_pool"], 25)
        with self.assertRaises(ValueError):
            self.decision.begin_offer("wrong-helper", 24, [24001], suanni_offer=True)
        self.decision.begin_offer("helper", 25, [25001], suanni_offer=True)
        self.assertEqual(self.decision.legal_actions(), [SeasonAction("select", 25001)])

    def test_unknown_unavailable_wrong_pool_or_unsupplied_skip_do_not_mutate(self):
        cases = [(1, [999], None, UnknownSeasonRule), (1, [1003], None, ValueError),
                 (1, [24001], None, ValueError), (1, [1001], self.skip_id, ValueError),
                 (1, [1001, 1001], None, ValueError), (999, [1001], None, UnknownSeasonRule)]
        before = self.decision.snapshot()
        for npc, candidates, skip, error in cases:
            with self.subTest(npc=npc, candidates=candidates), self.assertRaises(error):
                self.decision.begin_offer("invalid", npc, candidates, skip_strategy_id=skip)
            self.assertEqual(self.decision.snapshot(), before)

    def test_shared_pool_rejects_changing_the_locked_fate_within_one_match(self):
        self.decision.begin_offer("shared-first", 26, [26001])
        self.decision.step(SeasonAction("select", 26001))
        before = self.decision.snapshot()
        self.assertEqual(before["shared_pool_locks"], {"26": 26001})
        with self.assertRaisesRegex(ValueError, "changed within this match"):
            self.decision.begin_offer("shared-later", 26, [26002])
        self.assertEqual(self.decision.snapshot(), before)
        self.decision.begin_offer("shared-later", 26, [26001])

    def test_unknown_first_skip_target_fails_before_state_commit(self):
        self.decision.begin_offer("unknown-followup", 2, [2001, self.skip_id], skip_strategy_id=self.skip_id)
        before = self.decision.snapshot()
        with self.assertRaisesRegex(UnknownSeasonRule, "follow-up pool"):
            self.decision.step(SeasonAction("skip", self.skip_id))
        self.assertEqual(self.decision.snapshot(), before)
        self.decision.step(SeasonAction("select", 2001))

    def test_pending_offer_cannot_be_overwritten_and_snapshot_is_detached(self):
        state = self.begin_normal()
        state["offer"]["candidate_ids"].append(999)
        self.assertNotIn(SeasonAction("select", 999), self.decision.legal_actions())
        before = self.decision.snapshot()
        with self.assertRaises(ValueError):
            self.decision.begin_offer("overwrite", 1, [1001])
        self.assertEqual(self.decision.snapshot(), before)

    def test_no_local_candidate_sampling_or_effect_claims(self):
        with self.assertRaisesRegex(UnknownSeasonRule, "supply observed candidates"):
            self.decision.generate_offer(round_number=1, seed=2026)
        contract = self.catalog.contract()
        self.assertEqual(contract["season_mec"], 10)
        self.assertFalse(contract["candidate_generation_implemented"])
        self.assertFalse(contract["effect_execution_implemented"])
        self.assertEqual(len(contract["source_sha256"]), 64)

    def test_extracted_local_catalog_can_be_loaded_without_guessing_candidates(self):
        catalog = SeasonCatalog.from_local()
        self.assertGreater(len(catalog.npcs), 20)
        self.assertGreater(len(catalog.strategies), 700)
        self.assertIn("source_sha256", catalog.evidence)
        self.assertEqual(SeasonDecision(catalog).legal_actions(), [])


if __name__ == "__main__":
    unittest.main()
