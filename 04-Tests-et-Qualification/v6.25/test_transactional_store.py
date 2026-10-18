import unittest, tempfile, sys, sqlite3
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'03-Sources'))
from transactional_store import save_snapshot,load_snapshot,connect,migrate
class TestStore(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.db=Path(self.tmp.name)/'test.db'
 def tearDown(self): self.tmp.cleanup()
 def test_roundtrip(self):
  key=save_snapshot(self.db,[{'id':'b'},{'id':'a'}]);self.assertEqual(load_snapshot(self.db,key),[{'id':'a'},{'id':'b'}])
 def test_idempotent(self):
  a=[{'id':'b'},{'id':'a'}];self.assertEqual(save_snapshot(self.db,a),save_snapshot(self.db,list(reversed(a))))
 def test_duplicate(self):
  with self.assertRaises(ValueError):save_snapshot(self.db,[{'id':'x'},{'id':'x'}])
 def test_missing_id(self):
  with self.assertRaises(ValueError):save_snapshot(self.db,[{}])
 def test_missing_snapshot(self):
  save_snapshot(self.db,[])
  with self.assertRaises(KeyError):load_snapshot(self.db,'0'*64)
 def test_tampering(self):
  key=save_snapshot(self.db,[{'id':'x'}]);con=sqlite3.connect(self.db);con.execute('UPDATE snapshots SET payload=? WHERE id=?',('[]',key));con.commit();con.close()
  with self.assertRaises(ValueError):load_snapshot(self.db,key)
 def test_newer_schema_rejected(self):
  with connect(self.db) as con:
   con.execute('PRAGMA user_version=99')
   with self.assertRaises(ValueError):migrate(con)
 def test_fk(self):
  with connect(self.db) as con:
   migrate(con)
   with self.assertRaises(sqlite3.IntegrityError):con.execute('INSERT INTO snapshot_items VALUES (?,?,?)',('missing','x','{}'))
if __name__=='__main__':unittest.main()
