import unittest
from datetime import date
from month_view import MonthView

class FakeCalendar:
    def snapshot(self, as_of, horizon_days):
        return {'meetings':[{'id':'M1','title':'Revue','date':'2026-10-15','status':'DRAFT'}, {'id':'M2','title':'Autre','date':'2026-10-16','status':'CLOSED'}],
                'followups':[{'id':'F1','owner':'Alice','due_date':'2026-10-15','decision_id':'D1','description':'preuve'}, {'id':'F2','owner':'Bob','due_date':'2026-10-16','decision_id':'D2','description':'revue'}]}
class TestMonth(unittest.TestCase):
    def setUp(self):self.v=MonthView(FakeCalendar())
    def test_month(self):
        data=self.v.build(2026,10)
        self.assertEqual(len(data['days']['2026-10-15']),2)
        self.assertEqual(sum(len(w) for w in data['weeks'])%7,0)
    def test_filter(self):
        data=self.v.build(2026,10,owner='alice',meeting_status='CLOSED')
        self.assertEqual(len(data['followups']),1)
        self.assertEqual(len(data['meetings']),1)
    def test_invalid(self):
        for year,month in [(2026,13),(2026,0),(0,1),(True,1)]:
            with self.assertRaises(ValueError):self.v.build(year,month)
if __name__=='__main__':unittest.main()
