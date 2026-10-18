import tempfile
import unittest
from pathlib import Path
from governance import Governance
from governance_extensions import overview, decision_readiness, export_snapshot

class ExtensionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.g = Governance(Path(self.temp.name)/'test.sqlite')
        self.g.propose('ADR-1','SAN','Multipath','architect')
    def tearDown(self):
        self.g.close()
        self.temp.cleanup()
    def test_dashboard(self):
        self.assertEqual(overview(self.g)['pending_approvals'],1)
    def test_blocking_readiness(self):
        self.g.add_reservation('R-1','ADR-1','PRA','ops')
        self.assertFalse(decision_readiness(self.g,'ADR-1')['ready_for_review'])
    def test_export(self):
        p=Path(self.temp.name)/'report.md'
        result=export_snapshot(self.g,p)
        self.assertEqual(result['report_sha256'],__import__('hashlib').sha256(p.read_bytes()).hexdigest())
    def test_reject_empty_actor(self):
        with self.assertRaises(ValueError): self.g.decide('ADR-1',' ','APPROVED')
    def test_audit_tamper_blocks_approval(self):
        self.g.db.execute("UPDATE audit SET payload='tampered' WHERE seq=1")
        self.g.db.commit()
        with self.assertRaises(ValueError): self.g.decide('ADR-1','committee','APPROVED')
        with self.assertRaises(ValueError): export_snapshot(self.g,Path(self.temp.name)/'x.md')

if __name__=='__main__': unittest.main()
