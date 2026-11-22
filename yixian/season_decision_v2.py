"""Opt-in offline skip rewards on the frozen externally-supplied offer adapter.

No offer sampling, fate execution, full-match integration or resume interface.
The ordinary repeat-skip reward is the current offer's tier, not the first tier.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy

from .season import SeasonAction, SeasonCatalog, SeasonDecision, UnknownSeasonRule


class SeasonDecisionV2(SeasonDecision):
    def __init__(self, catalog: SeasonCatalog, *, rerolls: int, rerolls_cap: int,
                 first_skip_used: bool = False):
        if (type(rerolls) is not int or type(rerolls_cap) is not int
                or not 0 <= rerolls <= rerolls_cap):
            raise ValueError("Supply explicit nonnegative rerolls within the current cap")
        super().__init__(catalog, first_skip_used=first_skip_used)
        self.rerolls = rerolls
        self.rerolls_cap = rerolls_cap
        self.skip_reward_receipts: list[dict] = []

    def step(self, action: SeasonAction | Mapping) -> dict:
        if isinstance(action, Mapping):
            if set(action) != {"kind", "strategy_id"}:
                raise ValueError("A season action needs exactly kind and strategy_id")
            action = SeasonAction(action["kind"], action["strategy_id"])
        if (not isinstance(action, SeasonAction) or type(action.strategy_id) is not int
                or action not in self.legal_actions()):
            raise ValueError("Action is not one of the supplied candidates")
        # Preflight before consuming the offer or its first-skip entitlement.
        offer = self._offer
        reward, tier = 0, None
        if action.kind == "skip":
            if offer["suanni_offer"]:
                raise UnknownSeasonRule("Skipping the Suan Ni follow-up itself is not established")
            npc = self.catalog.npcs[offer["npc_config_id"]]
            target = npc.get("specialSkip")
            if type(target) is not int or target not in (24, 25):
                raise UnknownSeasonRule("Unknown Suan Ni follow-up tier")
            tier = 1 if target == 24 else 2
            expected = {24: 3, 25: 5}[target]
            if (type(npc.get("skipGotReplaceChance")) is not int
                    or npc["skipGotReplaceChance"] != expected):
                raise UnknownSeasonRule("Skip reward configuration conflicts with the confirmed tier")
            if self.first_skip_used:
                reward = expected
        if (type(self.rerolls) is not int or type(self.rerolls_cap) is not int
                or not 0 <= self.rerolls <= self.rerolls_cap):
            raise ValueError("Resource balance is invalid")
        trial = deepcopy(self)
        receipt = SeasonDecision.step(trial, action)
        before = trial.rerolls
        trial.rerolls = min(trial.rerolls_cap, before + reward)
        grant = {
            "suan_ni_tier": tier,
            "requested_rerolls": reward,
            "credited_rerolls": trial.rerolls - before,
            "overflow_rerolls": reward - (trial.rerolls - before),
            "before": before, "after": trial.rerolls, "cap": trial.rerolls_cap,
            "source": "user-season-clarification-2026-11-12",
        }
        receipt["skip_reward"] = grant
        receipt["effects_applied"] = reward > 0
        receipt["fate_effects_applied"] = False
        receipt["scope"] = "offline_skip_reward_only"
        if action.kind == "skip":
            receipt["rule_gaps"] = [x for x in receipt["rule_gaps"]
                                    if not x.startswith("Do not apply configured skip rewards")]
            trial.skip_reward_receipts.append({"offer_id": receipt["offer_id"], **grant})
        trial._receipts[-1] = deepcopy(receipt)
        self.__dict__.update(trial.__dict__)
        return deepcopy(receipt)

    def snapshot(self) -> dict:
        result = super().snapshot()
        result.update({"scope": "offline_season_skip_rewards_only",
                       "rerolls": self.rerolls, "rerolls_cap": self.rerolls_cap,
                       "skip_reward_receipts": deepcopy(self.skip_reward_receipts),
                       "effects_applied": any(x["requested_rerolls"] > 0 for x in self.skip_reward_receipts),
                       "fate_effects_applied": False,
                       "full_match_integration": False, "exact_resume_supported": False})
        return result
