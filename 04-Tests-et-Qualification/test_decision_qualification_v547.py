"""Human evidence qualification tests. Author: Abdelhalim Talbi."""
import tempfile
import unittest
from pathlib import Path
from decision_qualification_v547 import QualificationStore, CRITERIA

class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store=QualificationStore(Path(self.tmp.name)/'governance.sqlite')
        self.store.create('D1','Architecture','Alice','2026-12-31','DOC-01')
        self.good={k:True for k in CRITERIA}
    def test_accept(self):
        result=self.store.qualify('D1','Bob','ACCEPT',self.good,'Revue effectuée')
        self.assertTrue(result['human_reviewed']);self.assertFalse(result['production_activation'])
        self.assertEqual(self.store.qualifications('D1')[0]['verdict'],'ACCEPT')
    def test_reject(self):
        self.store.qualify('D1','Bob','REJECT',{**self.good,'relevance':False},'Preuve inadéquate')
        self.assertEqual(self.store.qualifications()[0]['verdict'],'REJECT')
    def test_missing_criteria(self):
        with self.assertRaises(ValueError):self.store.qualify('D1','Bob','ACCEPT',{},'Review')
    def test_false_accept(self):
        with self.assertRaises(ValueError):self.store.qualify('D1','Bob','ACCEPT',{**self.good,'coverage':False},'Review')
    def test_bad_verdict(self):
        with self.assertRaises(ValueError):self.store.qualify('D1','Bob','UNKNOWN',self.good,'Review')
    def test_bad_actor(self):
        with self.assertRaises(ValueError):self.store.qualify('D1',' ','REJECT',self.good,'Review')
    def test_missing_decision(self):
        with self.assertRaises(KeyError):self.store.qualify('NO','Bob','REJECT',self.good,'Review')
    def test_multiple_reviews(self):
        self.store.qualify('D1','Bob','REJECT',self.good,'First')
        self.store.qualify('D1','Alice','ACCEPT',self.good,'Second')
        self.assertEqual(len(self.store.qualifications()),2)
    def test_corrupted_qualification(self):
        self.store.qualify('D1','Bob','ACCEPT',self.good,'Review')
        with self.store._connect() as db:db.execute("UPDATE evidence_qualifications SET verdict='REJECT'")
        with self.assertRaises(ValueError):self.store.qualifications()
    def test_missing_row(self):
        self.store.qualify('D1','Bob','ACCEPT',self.good,'Review')
        with self.store._connect() as db:db.execute('DELETE FROM evidence_qualifications')
        with self.assertRaises(ValueError):self.store.qualifications()
    def test_empty(self):self.assertEqual(self.store.qualifications(),[])
    def test_immutable_audit(self):
        self.store.qualify('D1','Bob','ACCEPT',self.good,'Review')
        self.assertTrue(self.store.governance_report()['audit_verified'])
