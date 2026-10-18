import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / '02-Compilation-Windows' / 'publish-transaction.py'
spec = importlib.util.spec_from_file_location('publisher', MODULE)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)

class PublicationFaultInjection(unittest.TestCase):
    def setup_dirs(self, base):
        root=base/'release'; root.mkdir()
        pending=base/'pending'; pending.mkdir()
        for name in ('dist','installer','portable','build-logs'):
            (root/name).mkdir(); (root/name/'payload.txt').write_text('OLD '+name)
            (pending/name).mkdir(); (pending/name/'payload.txt').write_text('NEW '+name)
        return root,pending
    def assert_old(self, root):
        for name in publisher.COMPONENTS:
            self.assertEqual((root/name/'payload.txt').read_text(),'OLD '+name)
        self.assertFalse((root/'.publish-backup').exists())
    def test_success(self):
        with tempfile.TemporaryDirectory() as d:
            root,pending=self.setup_dirs(Path(d))
            publisher.publish(root,pending)
            for name in publisher.COMPONENTS:
                self.assertEqual((root/name/'payload.txt').read_text(),'NEW '+name)
            self.assertFalse((root/'.publish-backup').exists())
    def test_injected_failures_all_8_moves(self):
        for step in range(1,9):
            with self.subTest(step=step), tempfile.TemporaryDirectory() as d:
                root,pending=self.setup_dirs(Path(d))
                with self.assertRaisesRegex(RuntimeError,'INJECTED_FAILURE'):
                    publisher.publish(root,pending,fail_after=step)
                self.assert_old(root)
    def test_unresolved_backup_blocks_publication(self):
        with tempfile.TemporaryDirectory() as d:
            root,pending=self.setup_dirs(Path(d))
            (root/'.publish-backup').mkdir()
            with self.assertRaisesRegex(RuntimeError,'Unresolved'):
                publisher.publish(root,pending)
            self.assertTrue((root/'.publish-backup').exists())
    def test_reject_empty_pending(self):
        with tempfile.TemporaryDirectory() as d:
            root,pending=self.setup_dirs(Path(d))
            for p in (pending/'dist').iterdir(): p.unlink()
            with self.assertRaisesRegex(ValueError,'Empty'):
                publisher.publish(root,pending)
            self.assert_old(root)

if __name__=='__main__': unittest.main()
