import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from governance import Governance
from committee import Committees
from planning import Planning
from traceability import Traceability
from portfolio import portfolio_snapshot

class PortfolioTests(unittest.TestCase):
    def test_empty(self):
        with TemporaryDirectory() as tmp:
            g=Governance(Path(tmp)/'db.sqlite'); Traceability(g); p=Planning(Committees(g))
            self.assertEqual(portfolio_snapshot(g,p,'2026-10-15')['metrics']['decisions'],0)
            g.close()
    def test_filter_and_pending(self):
        with TemporaryDirectory() as tmp:
            g=Governance(Path(tmp)/'db.sqlite'); Traceability(g); p=Planning(Committees(g))
            g.propose('ADR-1','Architecture','Justification','Alice')
            self.assertEqual(portfolio_snapshot(g,p,'2026-10-15')['metrics']['pending'],1)
            self.assertEqual(portfolio_snapshot(g,p,'2026-10-15',owner='Bob')['items'],[])
            g.close()
    def test_invalid_audit_blocks(self):
        with TemporaryDirectory() as tmp:
            g=Governance(Path(tmp)/'db.sqlite'); Traceability(g); p=Planning(Committees(g))
            g.propose('ADR-1','Architecture','Justification','Alice')
            g.db.execute("UPDATE audit SET hash='corrupted'")
            with self.assertRaises(ValueError):portfolio_snapshot(g,p,'2026-10-15')
            g.close()
if __name__=='__main__':unittest.main()
