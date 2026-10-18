import unittest, tempfile, hashlib
from pathlib import Path
from governance import Governance
from committee import Committees
from planning import Planning
from committee_calendar import CommitteeCalendar
class CalendarTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.g=Governance(Path(self.t.name)/'test.db');self.g.propose('D1','Test','Motif','alice');self.c=Committees(self.g);self.c.create('M1','Revue','2026-11-10','bob');self.c.link('M1','D1','bob');self.p=Planning(self.c);self.cal=CommitteeCalendar(self.p)
 def tearDown(self):self.g.db.close();self.t.cleanup()
 def test_calendar(self):self.assertEqual(len(self.cal.snapshot('2026-11-01',20)['meetings']),1)
 def test_calendar_window(self):self.assertEqual(len(self.cal.snapshot('2026-10-01',10)['meetings']),0)
 def test_overdue(self):
  self.p.add_followup('F1','M1','D1','bob','2026-10-01','Preuve','bob');self.assertEqual(self.cal.snapshot('2026-10-15')['overdue_count'],1)
 def test_reminder_draft(self):
  self.p.add_followup('F1','M1','D1','bob','2026-10-01','Preuve','bob');r=self.cal.reminders('2026-10-15');self.assertEqual(len(r),1);self.assertIn('non envoyé',r[0]['body'])
 def test_report_digest(self):
  body,digest=self.cal.report('2026-10-15');self.assertEqual(digest,hashlib.sha256(body.encode()).hexdigest())
 def test_invalid_horizon(self):
  for n in [0,367,True]:
   with self.assertRaises(ValueError):self.cal.snapshot('2026-10-15',n)
if __name__=='__main__':unittest.main()
