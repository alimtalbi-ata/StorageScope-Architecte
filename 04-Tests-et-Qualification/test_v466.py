import unittest
from governance import Governance
from traceability import Traceability
from committee import Committees
from planning import Planning
from portfolio import portfolio_snapshot

class SqlPaginationTests(unittest.TestCase):
    def setUp(self):
        self.g=Governance(':memory:')
        # sqlite3.Connection context managers commit/rollback; they do not close.
        self.addCleanup(self.g.close)
        self.t=Traceability(self.g)
        self.c=Committees(self.g)
        self.p=Planning(self.c)
        for i in range(120):
            self.g.propose(f'D-{i:03}',f'SAN design {i}','rationale','architect')
    def test_pagination_sql(self):
        first=portfolio_snapshot(self.g,self.p,limit=50,sort='id')
        self.assertEqual(first['total_matches'],120)
        self.assertEqual(len(first['items']),50)
        self.assertEqual(first['items'][0]['id'],'D-000')
        self.assertEqual(portfolio_snapshot(self.g,self.p,limit=50,offset=100,sort='id')['items'][0]['id'],'D-100')
    def test_filter_sql(self):
        r=portfolio_snapshot(self.g,self.p,query='design 11',limit=50)
        self.assertEqual(r['total_matches'],11)
        self.assertEqual(r['metrics']['pending'],11)
    def test_reject_bad_input(self):
        for kw in ({'limit':True},{'offset':-1},{'sort':'id;DROP TABLE decisions'}):
            with self.assertRaises(ValueError):portfolio_snapshot(self.g,self.p,**kw)
    def test_index_exists(self):
        portfolio_snapshot(self.g,self.p)
        names={x[0] for x in self.g.db.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        self.assertIn('ix_follow_dec',names)
if __name__=='__main__':unittest.main()
