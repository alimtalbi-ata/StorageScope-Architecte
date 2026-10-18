"""Transactional evidence qualification tests. Author: Abdelhalim Talbi."""
import json
import tempfile
import unittest
from pathlib import Path
from decision_qualification_v547 import QualificationStore, CRITERIA
from architecture_decisions_v536 import ClosingConnection

class SnapshotQualificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = QualificationStore(Path(self.temp.name) / 'store.db')
        self.store.create('D1', 'Decision', 'Alice', '2026-12-31', 'DOC-1')
        self.good = dict.fromkeys(CRITERIA, True)
    def qualify(self):
        return self.store.qualify('D1','Bob','ACCEPT',self.good,'Revue')
    def test_connection_is_closing(self):
        with self.store._connect() as db: self.assertIsInstance(db, ClosingConnection)
        with self.assertRaises(Exception): db.execute('SELECT 1')
    def test_read_uses_single_connection(self):
        self.qualify()
        original = self.store._connect
        calls=[]
        def tracked():
            calls.append(True)
            return original()
        self.store._connect = tracked
        self.assertEqual(len(self.store.qualifications()),1)
        self.assertEqual(len(calls),1)
    def test_history_order(self):
        self.qualify()
        self.store.qualify('D1','Alice','REJECT',self.good,'Revue 2')
        entries=self.store.qualifications()
        self.assertEqual([e['verdict'] for e in entries],['ACCEPT','REJECT'])
        self.assertLess(entries[0]['audit_seq'],entries[1]['audit_seq'])
    def test_filtered_read_checks_unrelated_tampering(self):
        self.qualify()
        self.store.create('D2','Other','Alice','2026-12-31','DOC-2')
        self.store.qualify('D2','Bob','ACCEPT',self.good,'Revue')
        with self.store._connect() as db:
            db.execute("UPDATE evidence_qualifications SET verdict='REJECT' WHERE decision_id='D2'")
        with self.assertRaises(ValueError): self.store.qualifications('D1')
    def test_invalid_json(self):
        self.qualify()
        with self.store._connect() as db: db.execute("UPDATE evidence_qualifications SET criteria='{' ")
        with self.assertRaises(ValueError): self.store.qualifications()
    def test_invalid_criterion_type(self):
        self.qualify()
        with self.store._connect() as db:
            db.execute('UPDATE evidence_qualifications SET criteria=?',(json.dumps(dict.fromkeys(CRITERIA,1)),))
        with self.assertRaises(ValueError): self.store.qualifications()
    def test_missing_criterion(self):
        self.qualify()
        with self.store._connect() as db: db.execute('UPDATE evidence_qualifications SET criteria=?',('{}',))
        with self.assertRaises(ValueError): self.store.qualifications()
    def test_invalid_verdict(self):
        self.qualify()
        with self.store._connect() as db: db.execute("UPDATE evidence_qualifications SET verdict='UNKNOWN'")
        with self.assertRaises(ValueError): self.store.qualifications()
    def test_missing_audit_row(self):
        self.qualify()
        with self.store._connect() as db: db.execute('DELETE FROM evidence_qualifications')
        with self.assertRaises(ValueError): self.store.qualifications()
    def test_read_only_never_activates(self):
        self.qualify()
        self.assertFalse(self.store.qualifications()[0]['production_activation'])
    def test_empty_filter(self):
        self.qualify()
        self.assertEqual(self.store.qualifications('NONEXISTENT'),[])
    def test_integrity_head_present(self):
        self.qualify()
        self.assertTrue(self.store.report()['audit_verified'])
