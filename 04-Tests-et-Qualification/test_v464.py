import unittest
from unittest.mock import patch
from portfolio import portfolio_snapshot

class GovernanceSearchTests(unittest.TestCase):
    def setUp(self):
        self.g=type('G',(),{'db':type('D',(),{'execute':lambda self,q:[]})()})()
        self.p=object()
        self.snapshot={'decisions':[{'id':'ADR-02','title':'SAN migration','author':'Alice','status':'PROPOSED'}, {'id':'ADR-01','title':'NAS design','author':'Bob','status':'APPROVED'}], 'reservations':[], 'links':[], 'artifacts':[]}
    def run_query(self,**kw):
        with patch('portfolio.dashboard_snapshot',return_value=self.snapshot),patch('portfolio.CommitteeCalendar') as cal:
            cal.return_value.snapshot.return_value={'followups':[]}
            return portfolio_snapshot(self.g,self.p,**kw)
    def test_search_title(self):self.assertEqual([x['id'] for x in self.run_query(query='san')['items']],['ADR-02'])
    def test_priority(self):self.assertEqual([x['id'] for x in self.run_query(priority='ATTENTION')['items']],['ADR-02'])
    def test_sort_id(self):self.assertEqual([x['id'] for x in self.run_query(sort='id')['items']],['ADR-01','ADR-02'])
    def test_limit(self):
        r=self.run_query(limit=1);self.assertTrue(r['truncated']);self.assertEqual(r['total_matches'],2)
    def test_bad_sort(self):
        with self.assertRaises(ValueError):self.run_query(sort='invalid')
    def test_bad_limit(self):
        with self.assertRaises(ValueError):self.run_query(limit=0)
    def test_ui_wired(self):
        source=open('desktop.py').read()
        for term in ('portfolio_query','portfolio_priority','portfolio_sort','<Return>'):self.assertIn(term,source)
if __name__=='__main__':unittest.main()
