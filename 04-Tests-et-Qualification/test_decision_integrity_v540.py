import tempfile
import unittest
from pathlib import Path
from decision_governance_v537 import GovernanceStore
from decision_integrity_v540 import consistency_report, verified_review, decision_detail

class DecisionIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=GovernanceStore(Path(self.tmp.name)/'d.sqlite')
        self.store.create('D1','Stockage','Architecte','2026-10-10','PREUVE-1')
    def tearDown(self): self.tmp.cleanup()
    def test_clean(self): self.assertTrue(consistency_report(self.store)['consistent'])
    def test_detail(self): self.assertEqual(decision_detail(self.store,'D1')['decision']['id'],'D1')
    def test_missing_detail(self):
        with self.assertRaises(KeyError): decision_detail(self.store,'unknown')
    def test_review(self): self.assertTrue(verified_review(self.store)['consistency']['consistent'])
    def test_state_tamper(self):
        with self.store._connect() as db: db.execute("UPDATE decisions SET status='CLOSED' WHERE id='D1'")
        self.assertIn('decision_state_mismatch', [x['code'] for x in consistency_report(self.store)['issues']])
        with self.assertRaises(ValueError): verified_review(self.store)
    def test_immutable_tamper(self):
        with self.store._connect() as db: db.execute("UPDATE decisions SET owner='other' WHERE id='D1'")
        self.assertFalse(consistency_report(self.store)['consistent'])
    def test_orphan_link(self):
        with self.store._connect() as db: db.execute("INSERT INTO decision_links VALUES ('other','a','b','c','d','e','f')")
        self.assertIn('orphan_link',[x['code'] for x in consistency_report(self.store)['issues']])
    def test_unlogged_link(self):
        with self.store._connect() as db: db.execute("INSERT INTO decision_links VALUES ('D1','a','b','c','d','e','f')")
        self.assertIn('link_audit_mismatch',[x['code'] for x in consistency_report(self.store)['issues']])
    def test_unlogged_followup(self):
        with self.store._connect() as db: db.execute("INSERT INTO decision_followups VALUES ('D1','2026-10-10','A','N')")
        self.assertIn('followup_audit_mismatch',[x['code'] for x in consistency_report(self.store)['issues']])
    def test_transition(self):
        self.store.transition('D1','IN_REVIEW','actor','review')
        self.assertTrue(consistency_report(self.store)['consistent'])
    def test_audit_corruption(self):
        with self.store._connect() as db: db.execute("UPDATE decision_audit SET payload='{}' WHERE seq=1")
        with self.assertRaises(ValueError): consistency_report(self.store)

if __name__=='__main__': unittest.main()
