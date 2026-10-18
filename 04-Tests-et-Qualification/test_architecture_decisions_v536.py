import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from architecture_decisions_v536 import DecisionStore

class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'decisions.db'; self.db=DecisionStore(self.path)
    def create(self):
        return self.db.create('ADR-1','SAN performance','Architect','2026-11-30','sha256:abc')
    def test_create(self): self.assertEqual(self.create()['status'],'OPEN')
    def test_duplicate(self):
        self.create()
        with self.assertRaises(ValueError): self.create()
    def test_missing_owner(self):
        with self.assertRaises(ValueError): self.db.create('x','s','','2026-11-30','proof')
    def test_invalid_date(self):
        with self.assertRaises(ValueError): self.db.create('x','s','owner','not-date','proof')
    def test_transitions(self):
        self.create();self.db.transition('ADR-1','IN_REVIEW','Architect','Review started')
        self.db.transition('ADR-1','APPROVED','Board','Validated',approval='Board-2026-10')
        self.assertEqual(self.db.transition('ADR-1','CLOSED','Architect','Archived')['status'],'CLOSED')
    def test_cannot_skip_review(self):
        self.create()
        with self.assertRaises(ValueError): self.db.transition('ADR-1','APPROVED','A','r',approval='B')
    def test_approval_required(self):
        self.create();self.db.transition('ADR-1','IN_REVIEW','A','r')
        with self.assertRaises(ValueError): self.db.transition('ADR-1','APPROVED','A','r')
    def test_audit_integrity(self):
        self.create();self.assertTrue(self.db.report()['audit_verified'])
        with sqlite3.connect(self.path) as conn: conn.execute("UPDATE decision_audit SET payload='{}' WHERE seq=1")
        with self.assertRaises(ValueError): self.db.report()
    def test_export(self):
        self.create();target=Path(self.tmp.name)/'export.json'
        result=self.db.export(target)
        self.assertEqual(json.loads(target.read_text())['audit_head'],result['audit_head'])
    def test_read_only_policy(self):
        self.create();self.assertFalse(self.db.report()['production_activation'])
    def test_rejected(self):
        self.create();self.db.transition('ADR-1','IN_REVIEW','A','r')
        self.assertEqual(self.db.transition('ADR-1','REJECTED','A','not safe')['status'],'REJECTED')
