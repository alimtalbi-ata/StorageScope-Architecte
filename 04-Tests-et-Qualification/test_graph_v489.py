import unittest, sqlite3
from governance import Governance
from traceability import Traceability
from fast_dashboard import decision_graph
from graph_diagnostics import diagnose_routes
from route_scheduler import RouteCancelled

class V489Tests(unittest.TestCase):
    def test_graph_sql_indexes_and_limit(self):
        g=Governance(':memory:'); t=Traceability(g)
        try:
            g.propose('D1','title','rationale','author')
            for i in range(5):
                t.add('A'+str(i),'ACTION','task','author')
                t.link('D1','A'+str(i),'author')
            self.assertEqual(len(decision_graph(g.db,'D1')['artifacts']),5)
            self.assertEqual(len(decision_graph(g.db,'D1',limit=2)['artifacts']),2)
            with self.assertRaises(ValueError):decision_graph(g.db,'D1',limit=-1)
            indexes={r[1] for r in g.db.execute("PRAGMA index_list('reservations')")}
            self.assertIn('idx_reservations_decision_id',indexes)
            indexes={r[1] for r in g.db.execute("PRAGMA index_list('artifact_links')")}
            self.assertIn('idx_artifact_links_artifact_id',indexes)
        finally:g.close()
    def test_diagnostics_sample(self):
        routes=[[(i,0),(i,10)] for i in range(10)]
        r=diagnose_routes(routes,0,max_routes=3)
        self.assertEqual((r['sampled'],r['total'],r['complete']),(3,10,False))
    def test_diagnostics_cancel(self):
        with self.assertRaises(RouteCancelled):diagnose_routes([],0,cancel_check=lambda:True)
    def test_diagnostics_invalid(self):
        with self.assertRaises(ValueError):diagnose_routes([],0,max_routes=0)

if __name__=='__main__':unittest.main()
