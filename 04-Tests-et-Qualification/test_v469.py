"""V4.69 async reader contract tests. Author: Abdelhalim Talbi."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from governance import Governance
from cursor_pagination import decision_page

class AsyncReaderTests(unittest.TestCase):
    def test_readonly_separate_connection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'test.db'
            writer=Governance(path)
            writer.propose('D1','Title','Reason','alice')
            reader=sqlite3.connect('file:'+path.as_posix()+'?mode=ro',uri=True)
            isolated=Governance.__new__(Governance)
            isolated.db=reader
            self.assertEqual(decision_page(isolated)['items'][0]['id'],'D1')
            with self.assertRaises(sqlite3.OperationalError): reader.execute("DELETE FROM decisions")
            reader.close();writer.close()
    def test_async_ui_contract(self):
        source=(Path(__file__).parent/'desktop.py').read_text()
        for fragment in ('threading.Thread(', 'queue.Queue()', 'self.after(80', 'generation != self._portfolio_generation', 'load_portfolio_readonly', 'self._async_cursor_page()'):
            self.assertIn(fragment,source)
    def test_no_worker_tk_access(self):
        source=(Path(__file__).parent/'desktop.py').read_text()
        worker=source.split('        def worker():',1)[1].split('        threading.Thread(',1)[0]
        self.assertNotIn('.configure(',worker)
        self.assertNotIn('.insert(',worker)
if __name__=='__main__':unittest.main()
