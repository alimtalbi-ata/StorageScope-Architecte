import tempfile
import unittest
from pathlib import Path
from decision_governance_v537 import GovernanceStore
from decision_committee_v538 import committee_dashboard, export_committee

class CommitteeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=GovernanceStore(Path(self.tmp.name)/'decisions.sqlite')
        self.store.create('D1','Incident SAN','Alice','2026-01-01','EV1')
        self.store.create('D2','Capacity','Bob','2027-01-01','EV2')
    def test_overdue(self):
        d=committee_dashboard(self.store,today='2026-10-16');self.assertEqual(d['agenda'][0]['priority'],'P1')
    def test_owner(self):self.assertEqual(len(committee_dashboard(self.store,owner='alice')['agenda']),1)
    def test_status(self):self.assertEqual(len(committee_dashboard(self.store,status='CLOSED')['agenda']),0)
    def test_deadline(self):self.assertEqual(len(committee_dashboard(self.store,deadline='overdue',today='2026-10-16')['agenda']),1)
    def test_invalid_status(self):
        with self.assertRaises(ValueError):committee_dashboard(self.store,status='bad')
    def test_invalid_deadline(self):
        with self.assertRaises(ValueError):committee_dashboard(self.store,deadline='bad')
    def test_invalid_owner(self):
        with self.assertRaises(ValueError):committee_dashboard(self.store,owner=' ')
    def test_json(self):
        p=Path(self.tmp.name)/'a.json';export_committee(self.store,p,format='json');self.assertIn('audit_head',p.read_text())
    def test_csv(self):
        p=Path(self.tmp.name)/'a.csv';export_committee(self.store,p,format='csv');self.assertIn('priority',p.read_text())
    def test_markdown(self):
        p=Path(self.tmp.name)/'a.md';export_committee(self.store,p);self.assertIn('comité',p.read_text())
    def test_bad_format(self):
        with self.assertRaises(ValueError):export_committee(self.store,Path(self.tmp.name)/'x',format='html')
    def test_no_activation(self):self.assertFalse(committee_dashboard(self.store)['production_activation'])

if __name__=='__main__':unittest.main()
