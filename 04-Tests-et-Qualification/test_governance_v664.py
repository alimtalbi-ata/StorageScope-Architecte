import unittest, pathlib, sys, sqlite3, tempfile, warnings, gc
from contextlib import closing
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'03-Sources'))
from governance_desktop import page_bounds, paginate_candidates
class SQLiteAndPaginationV664(unittest.TestCase):
 def test_test_fixtures_close_connections(self):
  for name in ('test_governance_v653.py','test_governance_v663.py'):
   s=(ROOT/'04-Tests-et-Qualification'/name).read_text()
   self.assertNotIn('with sqlite3.connect(',s)
   self.assertIn('with closing(sqlite3.connect(',s)
 def test_explicit_connection_release(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'test.db'
   with closing(sqlite3.connect(p)) as con:
    with con: con.execute('CREATE TABLE t(x)')
   with closing(sqlite3.connect(p)) as con:
    self.assertEqual(con.execute('SELECT count(*) FROM t').fetchone()[0],0)
 def test_last_page_bounds(self):
  self.assertEqual(page_bounds(100001,10000), (1000,1000))
 def test_paginate_keeps_original_indices(self):
  data=[(i, f'K{i}', {'asset_ids':[str(i)]}) for i in range(205)]
  self.assertEqual([i for i,_,_ in paginate_candidates(data,2)],[200,201,202,203,204])
if __name__=='__main__':unittest.main()
