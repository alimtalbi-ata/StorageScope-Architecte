"""Functional committee register tests. Author: Abdelhalim Talbi."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from decision_governance_v537 import GovernanceStore
from decision_committee_register_v557 import action_register,export_action_register

class RegisterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=GovernanceStore(str(Path(self.tmp.name)/'db.sqlite'))
        self.store.create('D1','Storage','Alice','2026-01-01','REF')
        self.store.create('D2','SAN','Bob','2027-01-01','REF')
    def register(self,**kwargs):return action_register(self.store,today='2026-10-16',**kwargs)
    def test_all(self):self.assertEqual(self.register()['total'],2)
    def test_owner(self):self.assertEqual(self.register(owner='Alice')['actions'][0]['decision_id'],'D1')
    def test_owner_no_match(self):self.assertEqual(self.register(owner='Nobody')['total'],0)
    def test_overdue(self):self.assertEqual(self.register(deadline='overdue')['actions'][0]['decision_id'],'D1')
    def test_upcoming(self):self.assertEqual(self.register(deadline='upcoming')['actions'][0]['decision_id'],'D2')
    def test_priority_invalid(self):
        with self.assertRaises(ValueError):self.register(priority='P0')
    def test_deadline_invalid(self):
        with self.assertRaises(ValueError):self.register(deadline='yesterday')
    def test_owner_invalid(self):
        with self.assertRaises(ValueError):self.register(owner=' ')
    def test_pending(self):self.assertEqual(self.register()['pending'],2)
    def test_no_committee_resolution_claim(self):self.assertFalse(self.register()['human_committee_resolution_recorded'])
    def test_json_export(self):
        path=Path(self.tmp.name)/'actions.json';export_action_register(self.store,path,format='json')
        self.assertEqual(json.loads(path.read_text())['total'],2)
    def test_csv_export(self):
        path=Path(self.tmp.name)/'actions.csv';export_action_register(self.store,path)
        with path.open(newline='') as f: rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),2);self.assertTrue(all(r['audit_head'] for r in rows))
    def test_export_invalid(self):
        with self.assertRaises(ValueError):export_action_register(self.store,Path(self.tmp.name)/'x',format='pdf')
