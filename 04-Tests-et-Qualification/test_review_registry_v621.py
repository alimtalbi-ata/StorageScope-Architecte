from contextlib import closing
import importlib.util, pathlib, tempfile, unittest, sqlite3
p=pathlib.Path(__file__).resolve().parents[1]/'03-Sources'/'review_registry_v621.py'
spec=importlib.util.spec_from_file_location('review_registry_v621',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
C={'indices':[0,1],'identity_evidence':['serial'],'sources':['a','b'],'conflicts':[]}
R={'reconciliation':{'candidates':[C]}}
class ReviewTests(unittest.TestCase):
 def test_key_stable(self):self.assertEqual(m.candidate_key(C),m.candidate_key(dict(C)))
 def test_approve(self):
  with tempfile.TemporaryDirectory() as d:
   db=pathlib.Path(d)/'x.sqlite'; result=m.decide(db,R,m.candidate_key(C),'APPROVED','operator','verified');self.assertFalse(result['inventory_changed'])
   with closing(sqlite3.connect(db)) as conn, conn:self.assertEqual(conn.execute('select count(*) from events').fetchone()[0],1)
 def test_duplicate_denied(self):
  with tempfile.TemporaryDirectory() as d:
   db=pathlib.Path(d)/'x.sqlite';m.decide(db,R,m.candidate_key(C),'REJECTED','operator','different asset')
   with self.assertRaises(ValueError):m.decide(db,R,m.candidate_key(C),'APPROVED','operator','retry')
 def test_unknown_denied(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):m.decide(pathlib.Path(d)/'x.sqlite',R,'bad','APPROVED','operator','reason')
 def test_missing_reason_denied(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):m.decide(pathlib.Path(d)/'x.sqlite',R,m.candidate_key(C),'APPROVED','operator','')
if __name__=='__main__':unittest.main()
