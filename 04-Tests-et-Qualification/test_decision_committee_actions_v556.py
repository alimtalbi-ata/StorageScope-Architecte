"""Committee action regression tests. Author: Abdelhalim Talbi."""
import json
import tempfile
import unittest
from pathlib import Path
from decision_governance_v537 import GovernanceStore
from decision_committee_actions_v556 import committee_actions, export_committee_actions

class CommitteeActionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=GovernanceStore(str(Path(self.tmp.name)/'db.sqlite'))
        self.store.create('D1','Storage architecture','owner','2026-12-01','REF-1')
    def test_reference_present(self):
        self.assertNotIn('REFERENCE_ABSENTE',committee_actions(self.store,today='2026-10-16')['actions'][0]['missing_evidence'])
    def test_missing_link(self):
        self.assertIn('PREUVE_LIEE_ABSENTE',committee_actions(self.store,today='2026-10-16')['actions'][0]['missing_evidence'])
    def test_owner(self):
        self.assertEqual(committee_actions(self.store)['actions'][0]['owner'],'owner')
    def test_deadline(self):
        self.assertEqual(committee_actions(self.store)['actions'][0]['due_date'],'2026-12-01')
    def test_human_decision(self):
        self.assertTrue(committee_actions(self.store)['actions'][0]['human_decision_required'])
    def test_no_activation(self):
        self.assertFalse(committee_actions(self.store)['production_activation'])
    def test_no_sufficiency(self):
        self.assertFalse(committee_actions(self.store)['evidence_sufficiency_verified'])
    def test_json(self):
        p=Path(self.tmp.name)/'out.json';export_committee_actions(self.store,p,format='json')
        self.assertEqual(json.loads(p.read_text())['actions'][0]['decision_id'],'D1')
    def test_md(self):
        p=Path(self.tmp.name)/'out.md';export_committee_actions(self.store,p)
        self.assertIn('Storage architecture',p.read_text())
    def test_invalid_format(self):
        with self.assertRaises(ValueError):export_committee_actions(self.store,Path(self.tmp.name)/'out',format='csv')
    def test_owner_filter(self):
        self.assertEqual(committee_actions(self.store,owner='other')['actions'],[])
