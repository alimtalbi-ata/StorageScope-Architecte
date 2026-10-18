"""Commit boundary and partial cleanup crash tests, v6.84."""
import importlib.util, tempfile, unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'02-Compilation-Windows'/'publish-transaction.py'
spec=importlib.util.spec_from_file_location('pub684',P); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class BoundaryTests(unittest.TestCase):
    def setup_dirs(self,d):
        root,pending=Path(d)/'root',Path(d)/'pending'
        for base in (root,pending):
            for name in ('dist','installer'):(base/name).mkdir(parents=True)
        for name in ('dist','installer'):
            (root/name/'file.bin').write_text('old-'+name)
            (pending/name/'file.bin').write_text('new-'+name)
        return root,pending
    def test_crash_immediately_after_commit(self):
        with tempfile.TemporaryDirectory() as d:
            root,pending=self.setup_dirs(d)
            with self.assertRaises(SystemExit):m.publish(root,pending,crash_after_commit=True)
            m.recover(root)
            self.assertFalse((root/'.publish-backup').exists())
            for name in ('dist','installer'):self.assertEqual((root/name/'file.bin').read_text(),'new-'+name)
    def test_crash_during_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            root,pending=self.setup_dirs(d)
            with self.assertRaises(SystemExit):m.publish(root,pending,crash_during_cleanup=True)
            m.recover(root)
            self.assertFalse((root/'.publish-backup').exists())
            for name in ('dist','installer'):self.assertEqual((root/name/'file.bin').read_text(),'new-'+name)
    def test_crash_during_cleanup_with_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root,pending=self.setup_dirs(d)
            with self.assertRaises(SystemExit):m.publish(root,pending,crash_during_cleanup=True)
            (root/'dist'/'file.bin').write_text('tampered')
            with self.assertRaisesRegex(RuntimeError,'Committed publication mismatch'):m.recover(root)
            self.assertTrue((root/'.publish-backup').exists())
    def test_recovery_rejects_symlink_journal(self):
        with tempfile.TemporaryDirectory() as d:
            root,pending=self.setup_dirs(d);b=root/'.publish-backup';b.mkdir()
            (b/'real.json').write_text('{}');(b/'journal.json').symlink_to(b/'real.json')
            with self.assertRaisesRegex(RuntimeError,'Unsafe recovery'):m.recover(root)
