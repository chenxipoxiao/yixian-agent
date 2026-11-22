"""Decision receipts for externally supplied Hundred Schools season offers.

This module validates visible candidate IDs and records requests. It neither
samples the server's NPC schedule nor applies unimplemented fate effects. A
receipt is not proof that the game server accepted or applied the request.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

from .research import canonical_json

ROOT = Path(__file__).resolve().parents[1]


class UnknownSeasonRule(RuntimeError):
    """A server generation rule or an effect implementation is still missing."""


@dataclass(frozen=True)
class SeasonAction:
    kind: str
    strategy_id: int

    def to_dict(self):
        return asdict(self)


class SeasonCatalog:
    def __init__(self, npc_rows: list[dict], strategy_rows: list[dict], *, evidence: dict | None = None):
        self.npcs = self._index(npc_rows, "NPC")
        self.strategies = self._index(strategy_rows, "strategy")
        self.evidence = deepcopy(evidence or {})

    @staticmethod
    def _index(rows, label):
        result = {}
        for row in rows:
            if not isinstance(row, dict) or type(row.get("id")) is not int or row["id"] in result:
                raise ValueError(f"Invalid or duplicate {label} configuration id")
            canonical_json(row)
            result[row["id"]] = deepcopy(row)
        return result

    @classmethod
    def from_local(cls, tables: Path | str = ROOT / "data/local/2026-11-06/season",
                   evidence_path: Path | str = ROOT / "data/inspection/current-season-logic.json"):
        tables, evidence_path = Path(tables), Path(evidence_path)
        read = lambda path: json.loads(path.read_text(encoding="utf-8"))
        return cls(read(tables / "XianMoNpcConfig.json"), read(tables / "XianMoStrategyConfig.json"),
                   evidence=read(evidence_path))

    def contract(self):
        payload = {"npcs": list(self.npcs.values()), "strategies": list(self.strategies.values()),
                   "evidence": self.evidence}
        return {"mechanism": "XianMo", "season_mec": 10,
                "source_sha256": hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest(),
                "scope": "externally_supplied_offer_request_validation",
                "candidate_generation_implemented": False, "effect_execution_implemented": False}


class SeasonDecision:
    """Maintain selection intent for one match; authoritative state is external.

    pending IDs must be the actual supplied list. If a skip item is present,
    provide its exact ID separately as skip_strategy_id; the adapter never
    invents a magic skip ID. Shared pools accept exactly one non-skip candidate.
    """
    def __init__(self, catalog: SeasonCatalog, *, first_skip_used: bool = False):
        if type(first_skip_used) is not bool:
            raise ValueError("first_skip_used must be boolean")
        self.catalog = catalog
        self.first_skip_used = first_skip_used
        self.awaiting_suanni: int | None = None
        self._offer: dict | None = None
        self._receipts: list[dict] = []
        self._seen_offers: set[str] = set()
        self._shared_pool_locks: dict[int, int] = {}

    def begin_offer(self, offer_id: str, npc_config_id: int, candidate_ids: list[int], *,
                    skip_strategy_id: int | None = None, suanni_offer: bool = False):
        if self._offer is not None:
            raise ValueError("Resolve the existing offer before starting another")
        if not isinstance(offer_id, str) or not offer_id.strip() or offer_id in self._seen_offers:
            raise ValueError("Offer id must be nonempty and not previously consumed")
        if type(npc_config_id) is not int or npc_config_id not in self.catalog.npcs:
            raise UnknownSeasonRule("Unknown NPC configuration")
        if type(suanni_offer) is not bool:
            raise ValueError("suanni_offer must be boolean")
        if not isinstance(candidate_ids, list) or not candidate_ids or any(type(x) is not int for x in candidate_ids):
            raise ValueError("An explicit nonempty list of integer candidate IDs is required")
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("Duplicate candidate IDs")
        if skip_strategy_id is not None and (type(skip_strategy_id) is not int or skip_strategy_id not in candidate_ids):
            raise ValueError("Skip must use an ID present in the supplied pending list")
        if self.awaiting_suanni is not None:
            if not suanni_offer or npc_config_id != self.awaiting_suanni:
                raise ValueError("The first skip requires its externally supplied Suan Ni follow-up")
        elif suanni_offer:
            raise ValueError("No Suan Ni follow-up is pending")
        npc = self.catalog.npcs[npc_config_id]
        selectable = [x for x in candidate_ids if x != skip_strategy_id]
        if not 1 <= len(selectable) <= 3:
            raise ValueError("This offer adapter supports one to three supplied fate candidates")
        shared = bool(npc.get("isSinglePendingNpc", False))
        if shared and len(selectable) != 1:
            raise ValueError("A shared fate pool must supply one locked fate, not three independent choices")
        if shared and npc_config_id in self._shared_pool_locks and self._shared_pool_locks[npc_config_id] != selectable[0]:
            raise ValueError("The externally supplied shared fate changed within this match")
        for candidate in selectable:
            row = self.catalog.strategies.get(candidate)
            if row is None:
                raise UnknownSeasonRule(f"Unknown fate configuration {candidate}")
            if row.get("isAvailable") is not True:
                raise ValueError(f"Fate {candidate} is not marked available in this configuration snapshot")
            if row.get("npc") != npc_config_id:
                raise ValueError(f"Fate {candidate} does not belong to the supplied NPC pool")
        # All validation occurs before this state change.
        self._offer = {"id": offer_id, "npc_config_id": npc_config_id,
                       "candidate_ids": list(candidate_ids), "skip_strategy_id": skip_strategy_id,
                       "suanni_offer": suanni_offer, "shared_pool": shared}
        if shared:
            self._shared_pool_locks[npc_config_id] = selectable[0]
        return self.snapshot()

    def legal_actions(self) -> list[SeasonAction]:
        if self._offer is None:
            return []
        skip = self._offer["skip_strategy_id"]
        return [SeasonAction("skip" if value == skip else "select", value)
                for value in self._offer["candidate_ids"]]

    def step(self, action: SeasonAction | Mapping) -> dict:
        if isinstance(action, Mapping):
            if set(action) != {"kind", "strategy_id"}:
                raise ValueError("A season action needs exactly kind and strategy_id")
            action = SeasonAction(action["kind"], action["strategy_id"])
        if (not isinstance(action, SeasonAction) or type(action.strategy_id) is not int
                or action not in self.legal_actions()):
            raise ValueError("Action is not one of the externally supplied legal candidates")
        offer = self._offer
        npc = self.catalog.npcs[offer["npc_config_id"]]
        first_skip = self.first_skip_used
        awaiting = self.awaiting_suanni
        gaps = ["Effect execution and authoritative acknowledgement are external"]
        if action.kind == "skip":
            if not first_skip and not offer["suanni_offer"]:
                target = npc.get("specialSkip")
                if type(target) is not int or target not in self.catalog.npcs:
                    raise UnknownSeasonRule("First-skip follow-up pool is not known")
                first_skip, awaiting = True, target
                gaps.append("Await externally supplied Suan Ni candidates; do not sample them locally")
            elif offer["suanni_offer"]:
                awaiting = None
            gaps.append("Do not apply configured skip rewards without authoritative effect handling")
        else:
            if offer["suanni_offer"]:
                awaiting = None
            if self.catalog.strategies[action.strategy_id].get("_unknown_fields"):
                gaps.append("Selected fate contains expressions not yet decoded")
        receipt = {"offer_id": offer["id"], "npc_config_id": offer["npc_config_id"],
                   "action": action.to_dict(), "request_type": "SelectXianMoStrategyReq",
                   "shared_pool": offer["shared_pool"], "first_skip_used": first_skip,
                   "awaiting_suanni_pool": awaiting, "effects_applied": False,
                   "server_acknowledged": False, "rule_gaps": gaps}
        self.first_skip_used, self.awaiting_suanni = first_skip, awaiting
        self._seen_offers.add(offer["id"])
        self._receipts.append(deepcopy(receipt))
        self._offer = None
        return receipt

    def snapshot(self) -> dict:
        return {"first_skip_used": self.first_skip_used, "awaiting_suanni_pool": self.awaiting_suanni,
                "offer": deepcopy(self._offer), "receipts": deepcopy(self._receipts),
                "shared_pool_locks": {str(key): value for key, value in self._shared_pool_locks.items()},
                "scope": "selection_intent_only", "effects_applied": False,
                "candidate_generation_implemented": False}

    def generate_offer(self, *args, **kwargs):
        raise UnknownSeasonRule("NPC scheduling and candidate sampling rules are not recovered; supply observed candidates")
