import importlib.util
from pathlib import Path
import tempfile
import unittest

PATH = Path(__file__).resolve().parents[1] / '02-Compilation-Windows' / 'publish-transaction.py'
spec = importlib.util.spec_from_file_location('publisher681', PATH)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

class CrashRecoveryTests(unittest.TestCase):
    def setup_dirs(self, base, with_old=True):
        root, pending = base/'release', base/'pending'
        root.mkdir(); pending.mkdir()
        for name in p.COMPONENTS:
            if with_old:
                (root/name).mkdir(); (root/name/'data').write_text('OLD')
            (pending/name).mkdir(); (pending/name/'data').write_text('NEW')
        return root, pending

    def test_recover_all_crash_boundaries(self):
        for step in range(1, 9):
            with self.subTest(step=step), tempfile.TemporaryDirectory() as temp:
                root, pending = self.setup_dirs(Path(temp))
                with self.assertRaises(SystemExit):
                    p.publish(root, pending, crash_after=step)
                p.recover(root)
                self.assertFalse((root/'.publish-backup').exists())
                for name in p.COMPONENTS:
                    self.assertEqual((root/name/'data').read_text(), 'OLD')

    def test_recover_new_components_without_old_target(self):
        for step in range(1, 5):
            with self.subTest(step=step), tempfile.TemporaryDirectory() as temp:
                root, pending = self.setup_dirs(Path(temp), with_old=False)
                with self.assertRaises(SystemExit):
                    p.publish(root, pending, crash_after=step)
                p.recover(root)
                self.assertFalse(any((root/name).exists() for name in p.COMPONENTS))

    def test_missing_backup_blocks_without_deleting(self):
        with tempfile.TemporaryDirectory() as temp:
            root, pending = self.setup_dirs(Path(temp))
            with self.assertRaises(SystemExit):
                p.publish(root, pending, crash_after=2)
            import shutil
            shutil.rmtree(root/'.publish-backup'/'dist')
            with self.assertRaisesRegex(RuntimeError, 'Backup absent'):
                p.recover(root)
            self.assertEqual((root/'dist'/'data').read_text(), 'NEW')

    def test_no_implicit_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            root, pending = self.setup_dirs(Path(temp))
            with self.assertRaises(SystemExit):
                p.publish(root, pending, crash_after=1)
            with self.assertRaisesRegex(RuntimeError, 'Unresolved'):
                p.publish(root, pending)

if __name__ == '__main__': unittest.main()
