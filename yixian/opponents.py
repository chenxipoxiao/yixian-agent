"""Versioned opponent fixtures with whole-game splits and explicit observations.

This ingests normalized local records, not the entire community replay dataset.
Aggregated win rates and simulated outcomes must never become real-game labels.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .research import canonical_json, contract_digest, load_jsonl

SPLITS = ("train", "validation", "test")
OWN_SCALARS = frozenset({"character", "hp", "max_hp", "cultivation", "destiny", "qi", "def",
                         "round_number", "level", "exp", "rerolls", "alive"})
OWN_ARRAYS = frozenset({"cards", "hand_cards", "talents", "pending_choices", "season_choices"})
PUBLIC_SCALARS = frozenset({"character", "destiny", "cultivation", "level", "alive", "observed_round"})


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _fractions(values):
    if len(values) != 3 or any(type(x) not in (int, float) or not math.isfinite(x) or x < 0 for x in values):
        raise ValueError("Three nonnegative finite split fractions are required")
    if not math.isclose(sum(values), 1.0, abs_tol=1e-12):
        raise ValueError("Split fractions must sum to one")
    return tuple(values)


def split_for_game_id(game_id: str, *, salt="yixian-v1", fractions=(0.8, 0.1, 0.1)) -> str:
    """Stable by complete source game ID, independent of record order/viewpoint."""
    if not _text(game_id) or not _text(salt):
        raise ValueError("game_id and split salt must be nonempty strings")
    fractions = _fractions(fractions)
    data = canonical_json([salt, game_id.strip()]).encode("utf-8")
    value = int.from_bytes(hashlib.sha256(data).digest()[:8], "big") / 2**64
    if value < fractions[0]:
        return "train"
    if value < fractions[0] + fractions[1]:
        return "validation"
    return "test"


def assert_disjoint_games(partitions: Mapping[str, Iterable[str]]) -> None:
    seen = {}
    for split, game_ids in partitions.items():
        if split not in SPLITS or isinstance(game_ids, (str, bytes)):
            raise ValueError("Expected named splits containing complete game ids")
        for game_id in game_ids:
            if not _text(game_id):
                raise ValueError("Source game ids must be nonempty strings")
            normalized = game_id.strip()
            if normalized in seen and seen[normalized] != split:
                raise ValueError(f"Whole-game leakage: {normalized} occurs in {seen[normalized]} and {split}")
            seen[normalized] = split


def load_fixtures(path: str | Path) -> list[dict]:
    path = Path(path)
    if path.suffix.lower() == ".jsonl":
        return load_jsonl(path)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        data = data.get("records")
    if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
        raise ValueError("Fixture JSON must be an array or {records: [...]} object")
    canonical_json(data)
    return data


def build_opponent_library(records: Iterable[Mapping[str, Any]], contract: Mapping[str, Any], *,
                           split_salt="yixian-v1", fractions=(0.8, 0.1, 0.1)) -> dict:
    """Build a normalized, content-addressed library. Never infers real provenance.

    Each record needs id, evidence (synthetic/real_game), source.game_id,
    source.artifact, and battle. Real records additionally need a nonempty
    source.rules_version. Caller-declared splits are checked, not trusted.
    Arbitrary game fixture data stays environment-side; use player_view for policy.
    """
    digest = contract_digest(contract)
    fractions = _fractions(fractions)
    normalized, ids, group_metadata = [], set(), {}
    partitions = {split: set() for split in SPLITS}
    counts = {"synthetic": 0, "real_game": 0}
    for raw in records:
        if not isinstance(raw, Mapping):
            raise ValueError("Every opponent fixture must be an object")
        canonical_json(dict(raw))
        record = deepcopy(dict(raw))
        if not _text(record.get("id")) or record["id"] in ids:
            raise ValueError("Opponent fixture ids must be nonempty and unique")
        ids.add(record["id"])
        evidence = record.get("evidence")
        if evidence not in counts:
            raise ValueError("Opponent evidence must explicitly be synthetic or real_game")
        source = record.get("source")
        if not isinstance(source, dict) or not all(_text(source.get(k)) for k in ("game_id", "artifact")):
            raise ValueError("Every fixture needs source.game_id and source.artifact")
        source["game_id"] = source["game_id"].strip()
        if evidence == "real_game" and not _text(source.get("rules_version")):
            raise ValueError("Real-game records need a known source.rules_version")
        if evidence == "real_game" and _text(contract.get("rules_version")) and source["rules_version"] != contract["rules_version"]:
            raise ValueError("Real-game rules version differs from the library contract")
        if "engine_contract" in record and record["engine_contract"] != digest:
            raise ValueError("Fixture engine contract differs from the library contract")
        if not isinstance(record.get("battle"), dict) or not record["battle"]:
            raise ValueError("Every fixture needs a nonempty normalized battle object")
        if record.get("provenance_verified") is True:
            # Verified provenance requires a reference to a separate audit; even
            # that reference is not treated as an automatic game-rule verification.
            if evidence != "real_game" or not _text(source.get("verification_artifact")):
                raise ValueError("Verified real provenance needs a separate verification artifact")
        else:
            record["provenance_verified"] = False
        group = source["game_id"]
        metadata = (evidence, source.get("rules_version"))
        if group in group_metadata and group_metadata[group] != metadata:
            raise ValueError("Views from one game disagree on evidence type or rules version")
        group_metadata[group] = metadata
        split = split_for_game_id(group, salt=split_salt, fractions=fractions)
        if "split" in record and record["split"] != split:
            raise ValueError("Declared fixture split disagrees with its whole-game hash split")
        record["split"] = split
        record["engine_contract"] = digest
        normalized.append(record)
        partitions[split].add(group)
        counts[evidence] += 1
    if not normalized:
        raise ValueError("Cannot build an empty opponent library")
    normalized.sort(key=lambda record: record["id"])
    groups = {key: sorted(value) for key, value in partitions.items()}
    assert_disjoint_games(groups)
    body = {"schema_version": 1, "engine_contract": digest,
            "split_policy": {"method": "sha256_whole_game", "salt": split_salt, "fractions": list(fractions)},
            "records": normalized, "games_by_split": groups,
            "record_counts_by_evidence": counts,
            "scope": "normalized_fixture_library; not independent strength or current-rule validation"}
    return dict(body, library_digest=hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest())


def save_library(library: Mapping[str, Any], path: str | Path) -> None:
    body = dict(library)
    supplied = body.pop("library_digest", None)
    actual = hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
    if actual != supplied:
        raise ValueError("Opponent library content differs from its digest")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(library, ensure_ascii=False, indent=2), encoding="utf-8")


def _project_fields(source, scalars, arrays=()):
    if not isinstance(source, Mapping):
        raise ValueError("Player snapshot must be an object")
    projected = {}
    for key in scalars:
        if key not in source:
            continue
        value = source[key]
        if type(value) not in (str, int, float, bool) or (type(value) is float and not math.isfinite(value)):
            raise ValueError(f"Visible field {key} must be a finite scalar")
        projected[key] = value
    for key in arrays:
        if key not in source:
            continue
        value = source[key]
        if not isinstance(value, list) or any(type(item) not in (str, int) for item in value):
            raise ValueError(f"Visible field {key} must contain flat card/choice ids")
        projected[key] = list(value)
    return projected


def player_view(state: Mapping[str, Any], viewer_seat: int) -> dict:
    """Project policy observation with no opponent hand/current hidden board.

    Opponent public fields must be explicitly supplied in public_observations,
    keyed by seat as a string. Boards there are only last_seen_cards and require
    an observed_round no later than the current round. Raw opponent player state
    is never traversed. Snapshot visibility still needs real-client validation.
    """
    players = state.get("players")
    round_number = state.get("round_number")
    if not isinstance(players, list) or not 2 <= len(players) <= 8:
        raise ValueError("State needs two to eight player slots")
    if type(viewer_seat) is not int or not 0 <= viewer_seat < len(players):
        raise ValueError("Invalid viewer seat")
    if type(round_number) is not int or round_number < 1:
        raise ValueError("State needs a positive round_number")
    public = state.get("public_observations", {})
    if not isinstance(public, Mapping):
        raise ValueError("public_observations must be an object keyed by seat")
    opponents = []
    for seat in range(len(players)):
        if seat == viewer_seat:
            continue
        known = public.get(str(seat), {})
        visible = _project_fields(known, PUBLIC_SCALARS, ("last_seen_cards",))
        if "last_seen_cards" in visible and "observed_round" not in visible:
            raise ValueError("A last-seen board needs its observation round")
        if "observed_round" in visible:
            when = visible["observed_round"]
            if type(when) is not int or not 1 <= when <= round_number:
                raise ValueError("Future or invalid opponent observation round")
        opponents.append({"seat": seat, **visible})
    return {"schema_version": 1, "round_number": round_number, "viewer_seat": viewer_seat,
            "self": _project_fields(players[viewer_seat], OWN_SCALARS, OWN_ARRAYS), "opponents": opponents}
