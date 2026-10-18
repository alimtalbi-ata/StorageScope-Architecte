"""Crash at commit boundary and recovery validation (v6.83)."""
import importlib.util, tempfile, unittest, json
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'02-Compilation-Windows'/'publish-transaction.py'
spec=importlib.util.spec_from_file_location('publish683',P); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class CommitRecovery(unittest.TestCase):
    def setup_dirs(self,d):
        r,q=Path(d)/'root',Path(d)/'pending';(r/'dist').mkdir(parents=True);(q/'dist').mkdir(parents=True)
        (r/'dist'/'app.exe').write_text('old');(q/'dist'/'app.exe').write_text('new');return r,q
    def test_complete_journal_can_finalize(self):
        with tempfile.TemporaryDirectory() as d:
            r,q=self.setup_dirs(d);m.publish(r,q)
            (r/'.publish-backup'/'dist').mkdir(parents=True);(r/'.publish-backup'/'dist'/'app.exe').write_text('old')
            state={'schema':2,'phase':'complete','items':{'dist':{'had_target':True,'old_inventory':{'app.exe':m.digest(r/'.publish-backup'/'dist'/'app.exe')},'new_inventory':m.inventory(r/'dist')}}}
            (r/'.publish-backup'/'journal.json').write_text(json.dumps(state));m.recover(r)
            self.assertEqual((r/'dist'/'app.exe').read_text(),'new');self.assertFalse((r/'.publish-backup').exists())
    def test_complete_journal_tamper_blocks_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            r,q=self.setup_dirs(d);m.publish(r,q);b=r/'.publish-backup';b.mkdir()
            (b/'journal.json').write_text(json.dumps({'schema':2,'phase':'complete','items':{'dist':{'new_inventory':{'app.exe':'incorrect'}}}}))
            with self.assertRaisesRegex(RuntimeError,'Committed publication mismatch'):m.recover(r)
            self.assertTrue(b.exists())
    def test_journal_records_new_inventory(self):
        with tempfile.TemporaryDirectory() as d:
            r,q=self.setup_dirs(d)
            with self.assertRaises(SystemExit):m.publish(r,q,crash_after=1)
            state=json.loads((r/'.publish-backup'/'journal.json').read_text())
            self.assertEqual(state['items']['dist']['new_inventory'],m.inventory(q/'dist'))
            m.recover(r)
