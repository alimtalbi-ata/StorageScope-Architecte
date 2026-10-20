"""Regression tests for cross-table audit integrity and the read-only Windows view."""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from review_registry_v622 import candidate_key, decide, verify
from governance_desktop import history_for_selection, format_audit_event

CANDIDATE = {'asset_ids': ['NETAPP-001', 'FLASHBLADE-002'],
             'indices': [0, 1], 'identity_evidence': ['serial'],
             'conflicts': [], 'review_eligibility': 'REVIEW_REQUIRED',
             'review_key': 'valid'}
REPORT = {'reconciliation': {'candidates': [CANDIDATE]}}


class ReviewAuditIntegrityTests(unittest.TestCase):
    def create_registry(self, directory):
        db = Path(directory) / 'review.sqlite'
        key = candidate_key(CANDIDATE)
        decide(db, REPORT, key, 'APPROVED', 'reviewer', 'source cross-checked')
        return db, key

    def test_readonly_selected_history_and_full_digest(self):
        with tempfile.TemporaryDirectory() as d:
            db, key = self.create_registry(d)
            before = db.read_bytes()
            rows = history_for_selection(db, selected_key=key)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['candidate_key'], key)
            self.assertEqual(len(rows[0]['event_hash']), 64)
            self.assertIn(rows[0]['event_hash'], format_audit_event(rows[0]))
            self.assertEqual([], history_for_selection(db, selected_key='not-present'))
            self.assertEqual(before, db.read_bytes())

    def test_missing_registry_does_not_create_database(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / 'absent.sqlite'
            with self.assertRaises(FileNotFoundError):
                history_for_selection(db)
            self.assertFalse(db.exists())

    def test_tampered_decision_status_detected(self):
        with tempfile.TemporaryDirectory() as d:
            db, _ = self.create_registry(d)
            with sqlite3.connect(db) as conn:
                conn.execute("UPDATE decisions SET status='REJECTED'")
            self.assertFalse(verify(db)['valid'])
            with self.assertRaises(ValueError):
                history_for_selection(db)

    def test_tampered_decision_reason_detected(self):
        with tempfile.TemporaryDirectory() as d:
            db, _ = self.create_registry(d)
            with sqlite3.connect(db) as conn:
                conn.execute("UPDATE decisions SET reason='forged'")
            self.assertFalse(verify(db)['valid'])

    def test_duplicate_decision_rejected_without_audit_change(self):
        with tempfile.TemporaryDirectory() as d:
            db, key = self.create_registry(d)
            audit_before = history_for_selection(db)
            with self.assertRaises(ValueError):
                decide(db, REPORT, key, 'REJECTED', 'other', 'override')
            self.assertEqual(audit_before, history_for_selection(db))
            self.assertTrue(verify(db)['valid'])

    def test_multi_candidate_history_filter(self):
        with tempfile.TemporaryDirectory() as d:
            db, key1 = self.create_registry(d)
            second = {**CANDIDATE, 'asset_ids': ['ISILON-003', 'NETAPP-004']}
            key2 = candidate_key(second)
            decide(db, {'reconciliation': {'candidates': [second]}},
                   key2, 'REJECTED', 'reviewer', 'different assets')
            self.assertEqual(len(history_for_selection(db)), 2)
            self.assertEqual([key1], [r['candidate_key'] for r in history_for_selection(db, key1)])
            self.assertEqual([key2], [r['candidate_key'] for r in history_for_selection(db, key2)])
            self.assertTrue(verify(db)['valid'])


if __name__ == '__main__':
    unittest.main()
