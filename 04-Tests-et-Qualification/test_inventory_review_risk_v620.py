"""Regression tests for non-destructive inventory identity review."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "03-Sources"))
from inventory_review_risk_v620 import review_inventory
from governance_service import assess
from governance_desktop import explain_candidate, read_audit_history, history_for_selection, format_audit_event
from review_registry_v622 import decide, candidate_key, verify
import tempfile

class InventoryRiskTests(unittest.TestCase):
    def test_conflicting_wwn_is_high_risk(self):
        rows = [
            {"source": "A", "serial": "SN1", "wwn": "500a", "name": "array"},
            {"source": "B", "serial": "sn1", "wwn": "500b", "name": "array"},
        ]
        original = [dict(x) for x in rows]
        report = review_inventory(rows)
        self.assertEqual(rows, original)
        self.assertEqual(report["high_risk_count"], 1)
        self.assertEqual(report["candidates"][0]["identity_disagreements"], ["wwn"])
        self.assertTrue(report["candidates"][0]["review_required"])
        self.assertEqual(report["automatic_merges"], 0)

    def test_same_source_duplicate_requires_review(self):
        rows = [{"source": "A", "uuid": "X"}, {"source": "A", "uuid": "x"}]
        candidate = review_inventory(rows)["candidates"][0]
        self.assertTrue(candidate["same_source"])
        self.assertEqual(candidate["risk"], "MEDIUM")

    def test_governance_exposes_risk_and_keeps_human_review(self):
        rows = [
            {"source": "A", "id": "a", "name": "one", "type": "array", "serial": "S1", "wwn": "500a"},
            {"source": "B", "id": "b", "name": "two", "type": "array", "serial": "S1", "wwn": "500b"},
        ]
        report = assess(rows)
        candidate = report["reconciliation"]["candidates"][0]
        self.assertEqual(candidate["risk"], "HIGH")
        self.assertEqual(candidate["identity_disagreements"], ["wwn"])
        self.assertEqual(explain_candidate(candidate)["risk"], "HIGH")
        self.assertEqual(report["automatic_merges"], 0)

    def test_cli_cannot_approve_blocked_identity(self):
        rows = [
            {"source": "A", "id": "asset-a", "name": "one", "type": "array", "serial": "S1", "wwn": "500a"},
            {"source": "B", "id": "asset-b", "name": "two", "type": "array", "serial": "S1", "wwn": "500b"},
        ]
        report = assess(rows)
        candidate = report["reconciliation"]["candidates"][0]
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "audit.sqlite"
            with self.assertRaises(ValueError):
                decide(db, report, candidate_key(candidate),
                       "APPROVED", "reviewer", "test")
            self.assertFalse(db.exists(), "Blocked decision must not create an audit database")

    def test_authorized_decision_is_durable_and_auditable(self):
        rows = [
            {"source": "A", "id": "asset-a", "name": "one", "type": "array", "serial": "S1"},
            {"source": "B", "id": "asset-b", "name": "one", "type": "array", "serial": "S1"},
        ]
        report = assess(rows)
        candidate = report["reconciliation"]["candidates"][0]
        self.assertNotEqual(candidate["review_eligibility"], "BLOCKED_CONTRADICTION")
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "audit.sqlite"
            result = decide(db, report, candidate_key(candidate),
                            "APPROVED", "reviewer", "validated inventory evidence")
            self.assertFalse(result["inventory_changed"])
            self.assertTrue(db.is_file())
            self.assertTrue(verify(db)["valid"])
            self.assertEqual(verify(db)["decisions"], 1)
            with self.assertRaises(ValueError):
                decide(db, report, candidate_key(candidate),
                       "REJECTED", "reviewer", "duplicate immutable decision")
            self.assertTrue(verify(db)["valid"])
            self.assertEqual(verify(db)["decisions"], 1)

    def test_audit_history_read_only_and_selection_scoped(self):
        rows = [
            {"source": "NetApp", "id": "na-1", "name": "array", "type": "array", "serial": "SER-1"},
            {"source": "CMDB", "id": "cmdb-1", "name": "array", "type": "array", "serial": "SER-1"},
        ]
        report = assess(rows)
        key = candidate_key(report["reconciliation"]["candidates"][0])
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "review.sqlite"
            decide(db, report, key, "APPROVED", "architect", "validated by inventory owner")
            events = read_audit_history(db)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["candidate_key"], key)
            self.assertEqual(history_for_selection(db, key), events)
            self.assertEqual(history_for_selection(db, "unrelated-candidate"), [])
            self.assertIn(events[0]["event_hash"], format_audit_event(events[0]))
            self.assertTrue(verify(db)["valid"])

    def test_audit_history_rejects_tampered_chain(self):
        import sqlite3
        rows = [
            {"source": "NetApp", "id": "na-1", "name": "array", "type": "array", "serial": "SER-1"},
            {"source": "CMDB", "id": "cmdb-1", "name": "array", "type": "array", "serial": "SER-1"},
        ]
        report = assess(rows)
        key = candidate_key(report["reconciliation"]["candidates"][0])
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "review.sqlite"
            decide(db, report, key, "APPROVED", "architect", "validated")
            with sqlite3.connect(db) as connection:
                connection.execute("UPDATE audit SET reviewer=? WHERE candidate_key=?", ("tampered", key))
            self.assertFalse(verify(db)["valid"])
            with self.assertRaises(ValueError):
                read_audit_history(db)

    def test_clean_cross_source_candidate(self):
        rows = [{"source": "A", "serial": "X"}, {"source": "B", "serial": "x"}]
        candidate = review_inventory(rows)["candidates"][0]
        self.assertEqual(candidate["risk"], "LOW")
        self.assertTrue(candidate["review_required"])

if __name__ == "__main__":
    unittest.main()
