import tempfile
import unittest
from pathlib import Path
from governance import Governance
from traceability import Traceability
from fast_dashboard import summary_metrics,decision_graph,bounded_rows

class FastDashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.g=Governance(Path(self.tmp.name)/'test.db')
        self.trace=Traceability(self.g)
    def tearDown(self):
        self.g.close();self.tmp.cleanup()
    def test_empty(self):
        self.assertEqual(summary_metrics(self.g.db)['decisions'],0)
        self.assertEqual(bounded_rows(self.g.db,'decisions'),[])
    def test_counts_and_graph(self):
        self.g.propose('D1','Storage','reason','author')
        self.g.add_reservation('R1','D1','blocker','owner')
        self.trace.add('A1','ACTION','Verify','owner')
        self.trace.link('D1','A1','owner')
        self.assertEqual(summary_metrics(self.g.db)['blocking'],1)
        self.assertEqual(summary_metrics(self.g.db)['unfinished_actions'],1)
        self.assertEqual(decision_graph(self.g.db,'D1')['artifacts'][0]['id'],'A1')
    def test_bounded_and_unknown(self):
        for i in range(6):self.g.propose(f'D{i}','title','reason','author')
        self.assertEqual(len(bounded_rows(self.g.db,'decisions',2)),2)
        with self.assertRaises(ValueError):bounded_rows(self.g.db,'audit')
        with self.assertRaises(ValueError):bounded_rows(self.g.db,'decisions',1001)
        with self.assertRaises(ValueError):decision_graph(self.g.db,'missing')
    def test_sql_injection_not_possible(self):
        with self.assertRaises(ValueError):bounded_rows(self.g.db,'decisions;DROP TABLE decisions')
        self.assertEqual(summary_metrics(self.g.db)['decisions'],0)

if __name__=='__main__':unittest.main()
