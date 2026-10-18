import tempfile
import unittest
from pathlib import Path
from decision_governance_v537 import GovernanceStore
from decision_review_v539 import review_dossier, export_review

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=GovernanceStore(Path(self.temp.name)/'db.sqlite')
        self.store.create('D1','SAN','Alice','2026-01-01','EV1')
        self.store.create('D2','NAS','Bob','2027-01-01','EV2')
    def test_sheets(self):self.assertEqual(len(review_dossier(self.store,today='2026-10-16')['decision_sheets']),2)
    def test_owner_filter(self):self.assertEqual(len(review_dossier(self.store,owner='alice')['decision_sheets']),1)
    def test_overdue(self):self.assertEqual(review_dossier(self.store,today='2026-10-16')['decision_sheets'][0]['priority'],'P1')
    def test_unlinked(self):self.assertEqual(review_dossier(self.store)['decision_sheets'][0]['evidence_assessment'],'liens_absents')
    def test_no_production(self):self.assertFalse(review_dossier(self.store)['production_activation'])
    def test_no_false_certification(self):self.assertFalse(review_dossier(self.store)['evidence_sufficiency_verified'])
    def test_owner_counts(self):self.assertEqual(review_dossier(self.store)['owner_summary']['Alice']['count'],1)
    def test_json(self):
        p=Path(self.temp.name)/'report.json';export_review(self.store,p,format='json');self.assertIn('decision_sheets',p.read_text())
    def test_md(self):
        p=Path(self.temp.name)/'report.md';export_review(self.store,p);self.assertIn('Dossier de revue',p.read_text())
    def test_invalid_format(self):
        with self.assertRaises(ValueError):export_review(self.store,Path(self.temp.name)/'x',format='csv')
    def test_invalid_filter(self):
        with self.assertRaises(ValueError):review_dossier(self.store,status='INVALID')
    def test_corrupted_audit(self):
        with self.store._connect() as db:db.execute("UPDATE decision_audit SET entry_hash='bad' WHERE seq=1")
        with self.assertRaises(ValueError):review_dossier(self.store)
