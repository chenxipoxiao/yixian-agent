"""Transactional, append-only research memory with explicit evidence and roles.

Evidence references provide provenance, not an automatic authenticity guarantee.
All mutations append events. Corrections point to earlier events; experiment state
is derived from history. SQLite serializes writers, including separate processes.
"""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any
import uuid

from .research import canonical_json, contract_digest

ROLES = frozenset({"lead", "environment", "opponents", "training", "evaluation", "deployment"})
NOTE_KINDS = frozenset({"finding", "correction", "rule_decision", "lesson"})
CLAIMS = frozenset({"hypothesis", "measured", "verified"})
TRANSITIONS = {"registered": {"running", "failed", "cancelled"},
               "running": {"completed", "failed", "cancelled"},
               "completed": set(), "failed": set(), "cancelled": set()}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class Memory:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if str(path) == ":memory:":
            raise ValueError("Research memory needs a persistent file path")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    id TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    role TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    supersedes TEXT REFERENCES events(id),
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS events_no_update
                BEFORE UPDATE ON events BEGIN
                    SELECT RAISE(ABORT, 'research events are append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS events_no_delete
                BEFORE DELETE ON events BEGIN
                    SELECT RAISE(ABORT, 'research events are append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS events_no_replace
                BEFORE INSERT ON events
                WHEN EXISTS (SELECT 1 FROM events WHERE id=NEW.id OR seq=NEW.seq)
                BEGIN
                    SELECT RAISE(ABORT, 'research events are append-only');
                END;
            """)

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _validate_role(role):
        if role not in ROLES:
            raise ValueError(f"Unknown research role: {role}")

    @staticmethod
    def _event(row):
        result = dict(row)
        result["payload"] = json.loads(result["payload"])
        return result

    def _insert(self, db, kind, role, payload, supersedes=None):
        self._validate_role(role)
        serialized = canonical_json(dict(payload))
        if supersedes is not None:
            target = db.execute("SELECT kind FROM events WHERE id=?", (supersedes,)).fetchone()
            if target is None:
                raise ValueError("Correction references an unknown event")
            if target["kind"] not in NOTE_KINDS:
                raise ValueError("Experiments cannot be rewritten through corrections")
        previous = db.execute("SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        body = {
            "id": "event-" + uuid.uuid4().hex,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "kind": kind, "role": role, "payload": json.loads(serialized),
            "supersedes": supersedes, "previous_hash": previous[0] if previous else "",
        }
        digest = _sha(body)
        cursor = db.execute("""INSERT INTO events
            (id, created_at, kind, role, payload, supersedes, previous_hash, event_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (body["id"], body["created_at"], kind, role, serialized, supersedes, body["previous_hash"], digest))
        return dict(body, seq=cursor.lastrowid, event_hash=digest)

    def append(self, kind: str, role: str, payload: Mapping[str, Any], supersedes: str | None = None) -> str:
        """Append a typed finding/rule/lesson, returning its event id.

        Payload: statement, claim (hypothesis/measured/verified), evidence (list
        of artifact references). Measured and verified claims require evidence.
        A correction must name supersedes; no other kind may replace a finding.
        """
        self._validate_role(role)
        if kind not in NOTE_KINDS:
            raise ValueError("Use register_experiment/record_experiment for experiment events")
        if not isinstance(payload, Mapping) or not _text(payload.get("statement")):
            raise ValueError("A research note needs a nonempty statement")
        if payload.get("claim") not in CLAIMS:
            raise ValueError("Claim must be hypothesis, measured or verified")
        evidence = payload.get("evidence", [])
        if not isinstance(evidence, list) or any(not _text(ref) for ref in evidence):
            raise ValueError("evidence must be a list of nonempty artifact references")
        if payload["claim"] in {"measured", "verified"} and not evidence:
            raise ValueError("Measured or verified claims need evidence references")
        if (kind == "correction") != (supersedes is not None):
            raise ValueError("Only corrections require supersedes")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            return self._insert(db, kind, role, payload, supersedes)["id"]

    def register_experiment(self, config: Mapping[str, Any], contract: Mapping[str, Any], *, role="lead") -> str:
        """Freeze an experiment's configuration and complete engine contract."""
        if not isinstance(config, Mapping) or not config:
            raise ValueError("Experiment configuration must be a nonempty mapping")
        payload = {"experiment_id": "exp-" + uuid.uuid4().hex, "config": dict(config),
                   "contract": dict(contract), "contract_digest": contract_digest(contract),
                   "config_digest": _sha(dict(config)), "status": "registered"}
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._insert(db, "experiment_registered", role, payload)
        return payload["experiment_id"]

    def _experiment(self, db, experiment_id):
        events = [self._event(row) for row in db.execute(
            "SELECT * FROM events WHERE kind IN ('experiment_registered','experiment_status') ORDER BY seq")]
        history = [e for e in events if e["payload"].get("experiment_id") == experiment_id]
        if not history or history[0]["kind"] != "experiment_registered":
            raise ValueError("Unknown experiment id")
        return history

    def record_experiment(self, experiment_id: str, status: str, result: Mapping[str, Any] | None = None, *, role="training") -> str:
        """Append a valid lifecycle transition. Final states cannot be reopened."""
        if result is None:
            result = {}
        if not isinstance(result, Mapping):
            raise ValueError("Experiment result must be a mapping")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            history = self._experiment(db, experiment_id)
            current = history[-1]["payload"]["status"]
            if status not in TRANSITIONS[current]:
                raise ValueError(f"Invalid experiment transition: {current} -> {status}")
            return self._insert(db, "experiment_status", role,
                                {"experiment_id": experiment_id, "status": status, "result": dict(result)})["id"]

    def experiment(self, experiment_id: str) -> dict:
        with self._connect() as db:
            history = self._experiment(db, experiment_id)
        registration = history[0]["payload"]
        return {**registration, "status": history[-1]["payload"]["status"],
                "result": history[-1]["payload"].get("result", {}), "history": history}

    def events(self, *, kind: str | None = None) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM events ORDER BY seq" if kind is None else
                              "SELECT * FROM events WHERE kind=? ORDER BY seq", () if kind is None else (kind,))
            return [self._event(row) for row in rows]

    def verify_integrity(self) -> bool:
        previous = ""
        for event in self.events():
            digest = event.pop("event_hash")
            event.pop("seq")
            if event["previous_hash"] != previous or _sha(event) != digest:
                return False
            previous = digest
        return True

    def summary(self) -> dict:
        events = self.events()
        kinds, claims, experiments = {}, {}, {}
        for event in events:
            kinds[event["kind"]] = kinds.get(event["kind"], 0) + 1
            payload = event["payload"]
            if "claim" in payload:
                claims[payload["claim"]] = claims.get(payload["claim"], 0) + 1
            if event["kind"] in {"experiment_registered", "experiment_status"}:
                experiments[payload["experiment_id"]] = payload["status"]
        return {"events": len(events), "by_kind": kinds, "by_claim": claims,
                "experiments": experiments, "integrity_ok": self.verify_integrity(),
                "evidence_authenticity_verified": False}
