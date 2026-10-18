import tempfile,unittest
from pathlib import Path
from governance import Governance
from committee import Committees
from planning import Planning
class PlanningTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.g=Governance(Path(self.tmp.name)/'test.db');self.g.propose('D1','Architecture','raison','alice');self.c=Committees(self.g);self.c.create('M1','Revue','2026-11-10','bob');self.c.link('M1','D1','bob');self.p=Planning(self.c)
 def tearDown(self):self.g.db.close();self.tmp.cleanup()
 def test_agenda_decision(self):self.assertEqual(self.p.agenda('M1')['items'][0]['type'],'DECISION')
 def test_followup_and_close(self):
  self.p.add_followup('F1','M1','D1','bob','2026-10-01','Vérifier','bob');self.assertEqual(self.p.agenda('M1','2026-10-15')['items'][0]['priority'],1);self.p.complete('F1','bob','PV-001');self.assertFalse(any(x['type']=='FOLLOWUP' for x in self.p.agenda('M1')['items']))
 def test_invalid_link(self):
  with self.assertRaises(ValueError):self.p.add_followup('F1','M1','D2','bob','2026-11-01','test','bob')
 def test_missing_evidence(self):
  self.p.add_followup('F1','M1','D1','bob','2026-11-01','test','bob')
  with self.assertRaises(ValueError):self.p.complete('F1','bob','')
 def test_digest(self):
  body,digest=self.p.agenda_markdown('M1','2026-10-15');import hashlib;self.assertEqual(digest,hashlib.sha256(body.encode()).hexdigest())
 def test_audit(self):
  self.p.add_followup('F1','M1','D1','bob','2026-11-01','test','bob');self.assertTrue(self.g.verify_audit())
if __name__=='__main__':unittest.main()
