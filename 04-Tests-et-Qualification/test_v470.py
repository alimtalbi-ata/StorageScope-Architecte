"""v4.70 async search and cache tests. Author: Abdelhalim Talbi."""
import tempfile
import unittest
from pathlib import Path
from governance import Governance
from traceability import Traceability
from committee import Committees
from planning import Planning
from async_portfolio import load_portfolio_readonly

class AsyncFilteredTests(unittest.TestCase):
    def test_filtered_snapshot_readonly(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'data.sqlite3'
            g=Governance(path);Traceability(g);Planning(Committees(g))
            g.propose('D-1','Stockage','motif','alice')
            g.propose('D-2','Reseau','motif','bob')
            result=load_portfolio_readonly(path,mode='filtered',query='Stockage',limit=50,offset=0)
            self.assertEqual(result['total_matches'],1)
            self.assertEqual(result['items'][0]['id'],'D-1')
            self.assertEqual(load_portfolio_readonly(path,mode='cursor',limit=1)['items'][0]['id'],'D-1')
            g.close()
    def test_invalid_mode(self):
        with self.assertRaises(ValueError):load_portfolio_readonly('/does/not/exist',mode='bad')
    def test_async_filtered_ui_contract(self):
        source=(Path(__file__).parent/'desktop.py').read_text()
        for fragment in ("self._start_portfolio_worker('filtered'",'self._portfolio_cache','PRAGMA data_version','self._portfolio_generation','cache_key'):
            self.assertIn(fragment,source)
