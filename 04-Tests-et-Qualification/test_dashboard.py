import tempfile
import unittest
from pathlib import Path
from governance import Governance
from traceability import Traceability
from dashboard import dashboard_snapshot,graph_model

class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.g=Governance(Path(self.tmp.name)/'test.db');self.t=Traceability(self.g)
    def tearDown(self):
        self.g.close();self.tmp.cleanup()
    def test_empty(self):
        self.assertEqual(dashboard_snapshot(self.g)['metrics']['decisions'],0)
    def test_links_and_counts(self):
        self.g.propose('D1','Storage','Rationale','author')
        self.g.add_reservation('R1','D1','Concern','owner')
        self.t.add('A1','ACTION','Check','owner')
        self.t.link('D1','A1','owner')
        s=dashboard_snapshot(self.g)
        self.assertEqual(s['metrics']['blocking'],1)
        self.assertEqual(s['metrics']['unfinished_actions'],1)
        self.assertEqual(len(graph_model(s,'D1')['artifacts']),1)
    def test_unknown_decision(self):
        with self.assertRaises(ValueError):graph_model(dashboard_snapshot(self.g),'none')
    def test_tamper_rejected(self):
        self.g.propose('D1','Storage','Rationale','author')
        self.g.db.execute("UPDATE audit SET action='tampered'");self.g.db.commit()
        with self.assertRaises(ValueError):dashboard_snapshot(self.g)
if __name__=='__main__':unittest.main()
