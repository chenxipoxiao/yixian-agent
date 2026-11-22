"""Versioned research contracts, replay comparisons and offline promotion checks.

These checks validate supplied evidence and provenance metadata, not its authenticity.
Passing them does not establish strength against humans or permit online deployment.
No game rules are implemented here. All functions use the Python standard library.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


def _check_json(value: Any, path: str = "$") -> None:
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        # json.dumps below rejects NaN and infinity.
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path}: JSON object keys must be strings")
            _check_json(item, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_json(item, f"{path}[{index}]")
        return
    raise ValueError(f"{path}: unsupported JSON type {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Stable UTF-8 JSON representation; reject non-JSON and nonfinite values.

    This is a project-specific canonical form, not a claim of RFC 8785 compliance.
    Arrays retain their order. Integer and floating representations stay distinct.
    """
    _check_json(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def contract_digest(contract: Mapping[str, Any]) -> str:
    """Hash the complete engine contract, including any extra version fields.

    Callers should record engine revision, engine/data file hashes, rules_version,
    observation schema, action schema and capability flags in the contract.
    """
    if not isinstance(contract, Mapping) or not contract:
        raise ValueError("engine contract must be a nonempty JSON object")
    return hashlib.sha256(canonical_json(dict(contract)).encode("utf-8")).hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Read UTF-8 JSONL. Blank lines are allowed; malformed evidence is rejected."""
    records = []
    with Path(path).open("r", encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line, object_pairs_hook=_unique_object)
                canonical_json(record)
                if not isinstance(record, dict):
                    raise ValueError("record must be a JSON object")
            except (ValueError, TypeError) as error:
                raise ValueError(f"{path}:{line_number}: {error}") from error
            records.append(record)
    return records


@dataclass(frozen=True)
class Difference:
    path: str
    expected: Any
    observed: Any
    reason: str


def compare_expected(expected: Any, observed: Any, path: str = "$") -> list[Difference]:
    """Compare all recorded fields; observed objects may contain extra fields.

    Lists must have identical length and order. Numbers compare by value, but
    booleans do not compare equal to 0/1. No implicit numeric tolerance is used.
    """
    differences: list[Difference] = []
    if isinstance(expected, dict):
        if not isinstance(observed, dict):
            return [Difference(path, expected, observed, "type_mismatch")]
        for key in sorted(expected):
            field_path = f"{path}.{key}"
            if key not in observed:
                differences.append(Difference(field_path, expected[key], None, "missing_field"))
            else:
                differences.extend(compare_expected(expected[key], observed[key], field_path))
    elif isinstance(expected, list):
        if not isinstance(observed, list):
            return [Difference(path, expected, observed, "type_mismatch")]
        if len(expected) != len(observed):
            differences.append(Difference(path, len(expected), len(observed), "length_mismatch"))
        for index, (left, right) in enumerate(zip(expected, observed)):
            differences.extend(compare_expected(left, right, f"{path}[{index}]"))
    else:
        both_numbers = type(expected) in (int, float) and type(observed) in (int, float)
        if not both_numbers and type(expected) is not type(observed):
            differences.append(Difference(path, expected, observed, "type_mismatch"))
        elif expected != observed:
            differences.append(Difference(path, expected, observed, "value_mismatch"))
    return differences


@dataclass(frozen=True)
class ReplayResult:
    record_id: str
    evidence: str
    status: str
    source_match_id: str | None = None
    differences: tuple[Difference, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class ReplayReport:
    contract_digest: str
    rules_version: str | None
    records: tuple[ReplayResult, ...]
    real_game_matches: int
    simulator_self_checks: int
    failures: int
    real_source_match_ids: tuple[str, ...]


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_leaf(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_has_leaf(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_leaf(item) for item in value)
    return True


def check_replays(
    records: Iterable[Mapping[str, Any]],
    simulate: Callable[[dict[str, Any]], Any] | None = None,
    *,
    contract: Mapping[str, Any],
) -> ReplayReport:
    """Compare external game observations or explicitly synthetic self-checks.

    Every record needs id, evidence, input and expected. Evidence must be
    real_game or simulator_self_check. A real_game record additionally needs
    rules_version matching the contract and source.match_id/source.artifact.
    The source artifact is provenance metadata; this function does not read it.
    Supply simulate(input) or provide a recorded observed field. Simulator errors
    become failures. Empty expected objects and duplicate ids cannot pass.
    """
    digest = contract_digest(contract)
    version = contract.get("rules_version")
    if not _nonempty_text(version):
        version = None
    results: list[ReplayResult] = []
    seen: set[str] = set()
    for index, record in enumerate(records):
        record_id = str(record.get("id", f"line-{index + 1}")) if isinstance(record, Mapping) else f"line-{index + 1}"
        evidence = str(record.get("evidence", "unknown")) if isinstance(record, Mapping) else "unknown"
        source_match_id: str | None = None
        try:
            if not isinstance(record, Mapping):
                raise ValueError("record must be a JSON object")
            canonical_json(dict(record))
            if not _nonempty_text(record.get("id")):
                raise ValueError("id is required")
            if record_id in seen:
                raise ValueError("duplicate record id")
            seen.add(record_id)
            if evidence not in {"real_game", "simulator_self_check"}:
                raise ValueError("evidence must be real_game or simulator_self_check")
            if not isinstance(record.get("input"), dict):
                raise ValueError("input must be a JSON object")
            if "expected" not in record or not _has_leaf(record["expected"]):
                raise ValueError("expected must contain at least one recorded value")
            if "engine_contract" in record and record["engine_contract"] != digest:
                raise ValueError("record engine_contract does not match the current engine")
            if evidence == "real_game":
                if version is None or record.get("rules_version") != version:
                    raise ValueError("real-game rules_version must match a known contract version")
                source = record.get("source")
                if not isinstance(source, dict) or not all(_nonempty_text(source.get(key)) for key in ("match_id", "artifact")):
                    raise ValueError("real-game evidence requires source.match_id and source.artifact")
                source_match_id = source["match_id"].strip()
            if simulate is None and "observed" not in record:
                raise ValueError("supply a simulator or an observed result")
        except (ValueError, TypeError) as error:
            results.append(ReplayResult(record_id, evidence, "invalid", error=str(error)))
            continue
        try:
            observed = simulate(deepcopy(record["input"])) if simulate else record["observed"]
            canonical_json(observed)
        except Exception as error:
            results.append(ReplayResult(record_id, evidence, "simulator_error", source_match_id,
                                        error=f"{type(error).__name__}: {error}"))
            continue
        differences = tuple(compare_expected(record["expected"], observed))
        results.append(ReplayResult(record_id, evidence, "mismatch" if differences else "match",
                                    source_match_id, differences))
    real = [r for r in results if r.evidence == "real_game" and r.status == "match"]
    return ReplayReport(
        digest, version, tuple(results), len(real),
        sum(r.evidence == "simulator_self_check" and r.status == "match" for r in results),
        sum(r.status != "match" for r in results),
        tuple(sorted({r.source_match_id for r in real if r.source_match_id is not None})),
    )


@dataclass(frozen=True)
class PromotionDecision:
    ready: bool
    contract_digest: str
    blockers: tuple[str, ...]
    scope: str = "offline_research_only"


def _id_set(values: Iterable[str]) -> set[str]:
    if isinstance(values, (str, bytes)):
        raise ValueError("dataset ids must be a collection, not a string")
    result = set()
    for value in values:
        if not _nonempty_text(value):
            raise ValueError("dataset ids must be nonempty strings")
        result.add(value.strip())
    return result


def promotion_gate(
    contract: Mapping[str, Any],
    *,
    tests_passed: bool = False,
    full_match_environment: bool = False,
    replay_report: ReplayReport | None = None,
    training_ids: Iterable[str] = (),
    evaluation_ids: Iterable[str] = (),
    candidate_contract_digest: str | None = None,
    minimum_real_matches: int = 1,
) -> PromotionDecision:
    """Check prerequisites for advancing an offline full-match experiment.

    Split ids must identify whole games/families, not individual frames or turns.
    Counts and booleans are caller-supplied research evidence, not attestations.
    A passing result does not measure agent skill or certify simulator fidelity.
    """
    if type(minimum_real_matches) is not int or minimum_real_matches < 1:
        raise ValueError("minimum_real_matches must be a positive integer")
    digest = contract_digest(contract)
    blockers: list[str] = []
    if not _nonempty_text(contract.get("rules_version")):
        blockers.append("rules_version_missing")
    if contract.get("rules_verified") is not True:
        blockers.append("rules_not_verified")
    if tests_passed is not True:
        blockers.append("tests_not_passed")
    if full_match_environment is not True:
        blockers.append("full_match_environment_incomplete")
    if candidate_contract_digest is None:
        blockers.append("candidate_contract_missing")
    elif candidate_contract_digest != digest:
        blockers.append("candidate_contract_mismatch")
    if replay_report is None:
        blockers.append("real_game_evidence_missing")
    else:
        if replay_report.contract_digest != digest or replay_report.rules_version != contract.get("rules_version"):
            blockers.append("replay_contract_mismatch")
        if replay_report.failures:
            blockers.append("replay_failures")
        if len(replay_report.real_source_match_ids) < minimum_real_matches:
            blockers.append("insufficient_real_game_matches")
    training, evaluation = _id_set(training_ids), _id_set(evaluation_ids)
    if not training or not evaluation:
        blockers.append("dataset_split_missing")
    if training & evaluation:
        blockers.append("training_evaluation_overlap")
    return PromotionDecision(not blockers, digest, tuple(blockers))
