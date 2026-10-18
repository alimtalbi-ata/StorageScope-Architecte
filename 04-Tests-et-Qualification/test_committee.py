import tempfile,unittest
from pathlib import Path
from governance import Governance
from traceability import Traceability
from committee import Committees
class CommitteeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.g=Governance(Path(self.tmp.name)/'db.sqlite');self.t=Traceability(self.g);self.c=Committees(self.g)
  self.g.propose('D1','Design','Reason','author');self.c.create('M1','Architecture','2026-10-16T10:00','chair')
 def tearDown(self):self.g.close();self.tmp.cleanup()
 def test_attendee_and_report(self):
  self.c.attendee('M1','alice','architect','chair');self.c.link('M1','D1','chair');md,h=self.c.report('M1');self.assertIn('alice',md);self.assertEqual(len(h),64)
 def test_cannot_hold_without_attendee(self):
  with self.assertRaises(ValueError):self.c.hold('M1','chair','minutes')
 def test_closure_blocked(self):
  self.c.attendee('M1','alice','architect','chair');self.c.link('M1','D1','chair');self.c.hold('M1','chair','minutes')
  with self.assertRaises(ValueError):self.c.close('M1','chair',self.t)
 def test_close_after_evidence(self):
  self.c.attendee('M1','alice','architect','chair');self.c.link('M1','D1','chair');self.c.hold('M1','chair','minutes')
  self.t.add('E1','EVIDENCE','Test','alice','reference','alice');self.t.link('D1','E1','alice');self.t.complete('E1','alice','proof');self.g.decide('D1','chair','APPROVED')
  self.c.close('M1','chair',self.t);self.assertIn('CLOSED',self.c.report('M1')[0]);self.assertTrue(self.g.verify_audit())
 def test_immutable_after_hold(self):
  self.c.attendee('M1','alice','architect','chair');self.c.hold('M1','chair','minutes')
  with self.assertRaises(ValueError):self.c.attendee('M1','bob','architect','chair')
 def test_tamper_blocks(self):
  self.g.db.execute("UPDATE audit SET actor='bad' WHERE seq=1");self.g.db.commit()
  with self.assertRaises(ValueError):self.c.attendee('M1','alice','architect','chair')
if __name__=='__main__':unittest.main()
