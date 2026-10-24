import importlib.util, pathlib, tempfile, unittest, sqlite3
from contextlib import closing
p=pathlib.Path(__file__).resolve().parents[1]/'03-Sources'/'review_registry_v622.py'
s=importlib.util.spec_from_file_location('registry622',p); m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
C={'asset_ids':['SERIAL-B','SERIAL-A'],'indices':[3,9],'identity_evidence':['serial'],'conflicts':[]}
R={'reconciliation':{'candidates':[C]}}
class RegistryTests(unittest.TestCase):
 def test_order_independent(self):
  self.assertEqual(m.candidate_key(C),m.candidate_key({**C,'asset_ids':['SERIAL-A','SERIAL-B'],'indices':[0,1]}))
 def test_missing_ids_rejected(self):
  with self.assertRaises(ValueError):m.candidate_key({'indices':[0,1]})
 def test_duplicate_ids_rejected(self):
  with self.assertRaises(ValueError):m.candidate_key({'asset_ids':['A','a']})
 def test_audit(self):
  with tempfile.TemporaryDirectory() as d:
   db=pathlib.Path(d)/'db.sqlite'; r=m.decide(db,R,m.candidate_key(C),'APPROVED','reviewer','checked');self.assertFalse(r['inventory_changed']);self.assertTrue(m.verify(db)['valid'])
 def test_duplicate_rollback(self):
  with tempfile.TemporaryDirectory() as d:
   db=pathlib.Path(d)/'db.sqlite';key=m.candidate_key(C);m.decide(db,R,key,'REJECTED','reviewer','not same')
   with self.assertRaises(ValueError):m.decide(db,R,key,'APPROVED','reviewer','again')
   self.assertEqual(m.verify(db)['events_checked'],1)
 def test_tamper_detected(self):
  with tempfile.TemporaryDirectory() as d:
   db=pathlib.Path(d)/'db.sqlite';m.decide(db,R,m.candidate_key(C),'APPROVED','reviewer','verified')
   with closing(sqlite3.connect(db)) as conn:
    with conn:
     conn.execute("UPDATE audit SET action='REJECTED'")
   self.assertFalse(m.verify(db)['valid'])
 def test_missing_reason(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):m.decide(pathlib.Path(d)/'db.sqlite',R,m.candidate_key(C),'APPROVED','reviewer','')
if __name__=='__main__':unittest.main()
