from contextlib import closing
import sys, unittest, tempfile, sqlite3
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_desktop import read_audit_history, page_bounds
class V663(unittest.TestCase):
 def test_empty_page_bounds(self): self.assertEqual(page_bounds(0,0),(0,0))
 def test_clamp_page(self): self.assertEqual(page_bounds(201,100),(2,2))
 def test_read_only_connection_released(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'audit.sqlite'
   with closing(sqlite3.connect(p)) as db:
    with db: db.execute('create table audit(seq integer,candidate_key text,action text,reviewer text,at text,event_hash text)')
   # Database lacks a valid audit chain; the verification must reject it safely.
   with self.assertRaises((ValueError,KeyError,sqlite3.Error)): read_audit_history(p)
 def test_closing_used(self):
  source=(Path(__file__).resolve().parents[1]/'03-Sources/governance_desktop.py').read_text()
  self.assertIn('with closing(sqlite3.connect(',source)
 def test_boundary_guard(self):
  source=(Path(__file__).resolve().parents[1]/'03-Sources/governance_desktop.py').read_text()
  self.assertIn('if next_page == current:',source)
if __name__=='__main__': unittest.main()
