from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from yixian.memory import Memory
from yixian.research import contract_digest


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "research.sqlite3"
        self.memory = Memory(self.path)
        self.contract = {"engine": "test-only", "rules_version": "fixture-rules", "revision": "1"}

    def note(self, **overrides):
        return {"statement": "A hypothesis requiring a replay check", "claim": "hypothesis", **overrides}

    def test_correction_retains_original_and_survives_reopen(self):
        payload = self.note(details={"cards": ["a"]})
        original = self.memory.append("finding", "environment", payload)
        payload["details"]["cards"].append("changed")
        replacement = self.memory.append("correction", "evaluation",
            self.note(statement="Replay disproves the assumption", claim="verified", evidence=["replays/game-1.json"]),
            supersedes=original)
        events = Memory(self.path).events()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["payload"]["details"]["cards"], ["a"])
        self.assertEqual(events[1]["supersedes"], original)
        self.assertEqual(events[1]["id"], replacement)
        self.assertTrue(self.memory.verify_integrity())

    def test_sql_update_and_delete_are_blocked(self):
        self.memory.append("finding", "lead", self.note())
        with closing(sqlite3.connect(self.path)) as db:
            for sql in ("UPDATE events SET role='training'", "DELETE FROM events"):
                with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                    db.execute(sql)
        self.assertEqual(len(self.memory.events()), 1)

    def test_sql_replace_cannot_bypass_append_only_guards(self):
        event_id = self.memory.append("finding", "lead", self.note())
        with closing(sqlite3.connect(self.path)) as db:
            # SQLite REPLACE can skip DELETE triggers unless recursive_triggers
            # is enabled; reject both the id and primary-key collision directly.
            for new_id, new_seq in ((event_id, 2), ("another-id", 1)):
                with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                    db.execute("""INSERT OR REPLACE INTO events
                        (seq,id,created_at,kind,role,payload,previous_hash,event_hash)
                        VALUES (?,?,?,'finding','lead','{}','','')""", (new_seq, new_id, "changed"))
        self.assertEqual(self.memory.events()[0]["id"], event_id)
        self.assertTrue(self.memory.verify_integrity())

    def test_non_hypothesis_claims_need_artifact_references(self):
        for claim in ("measured", "verified"):
            with self.assertRaisesRegex(ValueError, "evidence"):
                self.memory.append("finding", "training", self.note(claim=claim))
            self.memory.append("finding", "evaluation", self.note(claim=claim, evidence=["evaluation.json"]))
        self.assertEqual(self.memory.summary()["by_claim"], {"measured": 1, "verified": 1})
        self.assertFalse(self.memory.summary()["evidence_authenticity_verified"])

    def test_invalid_notes_leave_no_partial_event(self):
        calls = [
            lambda: self.memory.append("finding", "invented-role", self.note()),
            lambda: self.memory.append("experiment_registered", "lead", self.note()),
            lambda: self.memory.append("finding", "lead", self.note(claim="proven")),
            lambda: self.memory.append("finding", "lead", self.note(evidence=[""])),
            lambda: self.memory.append("correction", "lead", self.note()),
            lambda: self.memory.append("correction", "lead", self.note(), supersedes="nonexistent"),
            lambda: self.memory.append("finding", "lead", self.note(), supersedes="nonexistent"),
            lambda: self.memory.append("finding", "lead", self.note(score=float("nan"))),
        ]
        for call in calls:
            with self.assertRaises(ValueError):
                call()
        self.assertEqual(self.memory.events(), [])

    def test_experiment_registration_freezes_config_and_contract(self):
        config = {"seed": 3, "model": {"hidden": [32, 32]}}
        experiment_id = self.memory.register_experiment(config, self.contract)
        original_digest = contract_digest(self.contract)
        config["model"]["hidden"][0] = 128
        self.contract["revision"] = "changed"
        experiment = self.memory.experiment(experiment_id)
        self.assertEqual(experiment["config"]["model"]["hidden"], [32, 32])
        self.assertEqual(experiment["contract_digest"], original_digest)
        self.assertEqual(experiment["status"], "registered")

    def test_lifecycle_is_append_only_and_cannot_skip_or_reopen(self):
        experiment_id = self.memory.register_experiment({"seed": 3}, self.contract)
        with self.assertRaisesRegex(ValueError, "transition"):
            self.memory.record_experiment(experiment_id, "completed", {"score": 1})
        self.memory.record_experiment(experiment_id, "running", {"started": True})
        self.memory.record_experiment(experiment_id, "completed", {"artifact": "checkpoint.npz"})
        with self.assertRaisesRegex(ValueError, "transition"):
            self.memory.record_experiment(experiment_id, "running")
        experiment = self.memory.experiment(experiment_id)
        self.assertEqual([e["payload"]["status"] for e in experiment["history"]], ["registered", "running", "completed"])
        self.assertEqual(experiment["result"], {"artifact": "checkpoint.npz"})
        self.assertEqual(self.memory.summary()["experiments"], {experiment_id: "completed"})

    def test_failure_before_start_retains_reason(self):
        experiment_id = self.memory.register_experiment({"seed": 3}, self.contract)
        self.memory.record_experiment(experiment_id, "failed", {"error": "unsupported rules"})
        self.assertEqual(self.memory.experiment(experiment_id)["result"]["error"], "unsupported rules")

    def test_experiment_history_cannot_be_overwritten_by_correction(self):
        self.memory.register_experiment({"seed": 3}, self.contract)
        event_id = self.memory.events()[0]["id"]
        with self.assertRaisesRegex(ValueError, "Experiments"):
            self.memory.append("correction", "lead", self.note(), supersedes=event_id)
        self.assertEqual(len(self.memory.events()), 1)

    def test_concurrent_writers_keep_single_intact_chain(self):
        def write(index):
            return Memory(self.path).append("lesson", "training", self.note(statement=f"trial {index}"))
        with ThreadPoolExecutor(max_workers=4) as pool:
            ids = list(pool.map(write, range(24)))
        self.assertEqual(len(set(ids)), 24)
        self.assertEqual(len(self.memory.events()), 24)
        self.assertTrue(self.memory.verify_integrity())

    def test_note_experiment_reference_does_not_become_lifecycle_event(self):
        self.memory.append("finding", "evaluation", self.note(experiment_id="reference-only"))
        self.assertEqual(self.memory.summary()["experiments"], {})


if __name__ == "__main__":
    unittest.main()
