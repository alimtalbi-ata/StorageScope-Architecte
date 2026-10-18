import unittest
from unittest.mock import patch
from portfolio import portfolio_snapshot
class PaginationTests(unittest.TestCase):
    def setUp(self):
        self.g=type('G',(),{'db':type('D',(),{'execute':lambda self,q:[]})()})()
        self.rows=[{'id':f'D-{i:03}','title':'Architecture','author':'A','status':'APPROVED'} for i in range(125)]
    def call(self,**kw):
        with patch('portfolio.dashboard_snapshot',return_value={'decisions':self.rows,'reservations':[],'links':[],'artifacts':[]}),patch('portfolio.CommitteeCalendar') as cal:
            cal.return_value.snapshot.return_value={'followups':[]}
            return portfolio_snapshot(self.g,object(),sort='id',**kw)
    def test_first_page(self):
        r=self.call(limit=50);self.assertEqual(len(r['items']),50);self.assertTrue(r['has_next']);self.assertEqual(r['metrics']['decisions'],125)
    def test_middle_page(self):
        r=self.call(limit=50,offset=50);self.assertEqual(r['items'][0]['id'],'D-050');self.assertTrue(r['has_previous'])
    def test_last_page(self):
        r=self.call(limit=50,offset=100);self.assertEqual(len(r['items']),25);self.assertFalse(r['has_next'])
    def test_out_of_range(self):self.assertEqual(self.call(limit=50,offset=200)['items'],[])
    def test_bad_offset(self):
        for x in (-1,True,1.2):
            with self.assertRaises(ValueError):self.call(offset=x)
    def test_ui_paging(self):
        source=open('desktop.py',encoding='utf-8').read();self.assertIn('portfolio_page',source);self.assertIn('portfolio_offset',source)
if __name__=='__main__':unittest.main()
