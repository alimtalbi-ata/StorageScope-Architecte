"""Security regressions for v6.82; run with python -m unittest."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
P = Path(__file__).resolve().parents[1] / '02-Compilation-Windows' / 'publish-transaction.py'
spec = importlib.util.spec_from_file_location('publisher_v682', P)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)
class SecurityTests(unittest.TestCase):
    def test_tampered_backup_blocks_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            r,q=Path(d)/'root',Path(d)/'stage'
            (r/'dist').mkdir(parents=True);(q/'dist').mkdir(parents=True)
            (r/'dist'/'a').write_text('old');(q/'dist'/'a').write_text('new')
            with self.assertRaises(SystemExit): publisher.publish(r,q,crash_after=1)
            (r/'.publish-backup'/'dist'/'a').write_text('tampered')
            with self.assertRaisesRegex(RuntimeError,'Corrupted backup'): publisher.recover(r)
    def test_staging_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r,q=Path(d)/'root',Path(d)/'stage'
            r.mkdir();q.mkdir();(q/'other').mkdir();(q/'other'/'a').write_text('x')
            (q/'dist').symlink_to(q/'other',target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'Unsafe staged'): publisher.publish(r,q)
    def test_backup_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r,q=Path(d)/'root',Path(d)/'stage'
            (r/'dist').mkdir(parents=True);(q/'dist').mkdir(parents=True)
            (r/'dist'/'a').write_text('old');(q/'dist'/'a').write_text('new')
            with self.assertRaises(SystemExit): publisher.publish(r,q,crash_after=1)
            old=r/'.publish-backup'/'dist';other=r/'saved';old.rename(other)
            old.symlink_to(other,target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError,'Symlinked'): publisher.recover(r)
