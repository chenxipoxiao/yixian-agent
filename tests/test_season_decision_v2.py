import unittest
from copy import deepcopy

from yixian.season import SeasonCatalog, UnknownSeasonRule
from yixian.season_decision_v2 import SeasonDecisionV2


def fixture():
    return SeasonCatalog([
        {"id": 1, "specialSkip": 24, "skipGotReplaceChance": 3},
        {"id": 6, "specialSkip": 25, "skipGotReplaceChance": 5},
        {"id": 24}, {"id": 25},
    ], [{"id": i, "npc": n, "isAvailable": True}
        for i, n in [(1001, 1), (6001, 6), (24001, 24), (25001, 25)]])


class SeasonSkipV2Tests(unittest.TestCase):
    def test_first_skip_followup_without_currency_then_repeat_uses_current_tier(self):
        d = SeasonDecisionV2(fixture(), rerolls=4, rerolls_cap=25)
        d.begin_offer("first", 1, [1001, -7], skip_strategy_id=-7)
        r = d.step({"kind": "skip", "strategy_id": -7})
        self.assertEqual((d.rerolls, r["awaiting_suanni_pool"]), (4, 24))
        d.begin_offer("helper", 24, [24001], suanni_offer=True)
        r = d.step({"kind": "select", "strategy_id": 24001})
        self.assertFalse(r["fate_effects_applied"])
        d.begin_offer("second", 6, [6001, -7], skip_strategy_id=-7)
        r = d.step({"kind": "skip", "strategy_id": -7})
        self.assertEqual((d.rerolls, r["awaiting_suanni_pool"]), (9, None))
        d.begin_offer("third", 1, [1001, -7], skip_strategy_id=-7)
        d.step({"kind": "skip", "strategy_id": -7})
        self.assertEqual(d.rerolls, 12)
        self.assertTrue(d.snapshot()["effects_applied"])
        self.assertFalse(d.snapshot()["fate_effects_applied"])

    def test_first_high_tier_skip_does_not_grant_five_rerolls(self):
        d = SeasonDecisionV2(fixture(), rerolls=0, rerolls_cap=25)
        d.begin_offer("first", 6, [6001, -7], skip_strategy_id=-7)
        r = d.step({"kind": "skip", "strategy_id": -7})
        self.assertEqual((d.rerolls, r["awaiting_suanni_pool"]), (0, 25))

    def test_repeat_reward_obeys_explicit_cap_and_records_overflow(self):
        for npc, fate, reward in [(1, 1001, 3), (6, 6001, 5)]:
            with self.subTest(npc=npc):
                d = SeasonDecisionV2(fixture(), rerolls=24, rerolls_cap=25, first_skip_used=True)
                d.begin_offer("repeat", npc, [fate, -7], skip_strategy_id=-7)
                r = d.step({"kind": "skip", "strategy_id": -7})
                self.assertEqual(d.rerolls, 25)
                self.assertEqual(r["skip_reward"]["requested_rerolls"], reward)
                self.assertEqual(r["skip_reward"]["credited_rerolls"], 1)
                self.assertEqual(r["skip_reward"]["overflow_rerolls"], reward-1)

    def test_duplicate_offer_or_action_cannot_reward_twice(self):
        d = SeasonDecisionV2(fixture(), rerolls=0, rerolls_cap=25, first_skip_used=True)
        d.begin_offer("repeat", 1, [1001, -7], skip_strategy_id=-7)
        d.step({"kind": "skip", "strategy_id": -7})
        before = d.snapshot()
        with self.assertRaises(ValueError):
            d.step({"kind": "skip", "strategy_id": -7})
        with self.assertRaises(ValueError):
            d.begin_offer("repeat", 1, [1001, -7], skip_strategy_id=-7)
        self.assertEqual(d.snapshot(), before)

    def test_conflicting_reward_fails_without_consuming_offer(self):
        c = fixture(); c.npcs[1]["skipGotReplaceChance"] = 5
        d = SeasonDecisionV2(c, rerolls=2, rerolls_cap=25, first_skip_used=True)
        d.begin_offer("repeat", 1, [1001, -7], skip_strategy_id=-7)
        before = d.snapshot()
        with self.assertRaises(UnknownSeasonRule):
            d.step({"kind": "skip", "strategy_id": -7})
        self.assertEqual(d.snapshot(), before)

    def test_unsupported_helper_skip_preserves_pending_state(self):
        d = SeasonDecisionV2(fixture(), rerolls=2, rerolls_cap=25)
        d.begin_offer("first", 1, [1001, -7], skip_strategy_id=-7)
        d.step({"kind": "skip", "strategy_id": -7})
        d.begin_offer("helper", 24, [24001, -7], skip_strategy_id=-7, suanni_offer=True)
        before = d.snapshot()
        with self.assertRaises(UnknownSeasonRule):
            d.step({"kind": "skip", "strategy_id": -7})
        self.assertEqual(d.snapshot(), before)

    def test_selection_does_not_grant_skip_reward_or_execute_fate(self):
        d = SeasonDecisionV2(fixture(), rerolls=2, rerolls_cap=25, first_skip_used=True)
        d.begin_offer("selection", 6, [6001, -7], skip_strategy_id=-7)
        r = d.step({"kind": "select", "strategy_id": 6001})
        self.assertEqual(d.rerolls, 2)
        self.assertFalse(r["effects_applied"])
        self.assertEqual(d.skip_reward_receipts, [])

    def test_real_local_npc_mappings_agree_with_user_rule(self):
        c = SeasonCatalog.from_local()
        for row in c.npcs.values():
            self.assertIn(row["specialSkip"], (24, 25))
            self.assertEqual(row["skipGotReplaceChance"], {24: 3, 25: 5}[row["specialSkip"]])


if __name__ == "__main__":
    unittest.main()
