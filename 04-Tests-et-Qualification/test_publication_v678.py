"""Historical publication contracts against the current recoverable publisher.

This tests the actual rollback and hash gates rather than obsolete PowerShell
implementation strings. No publication to user directories is performed.
Author: Abdelhalim Talbi.
"""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "02-Compilation-Windows" / "build-all-windows.ps1"
PUBLISHER = ROOT / "02-Compilation-Windows" / "publish-transaction.py"
spec = importlib.util.spec_from_file_location("publisher_v678", PUBLISHER)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class PublicationRollbackContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.root, self.pending = base / "release", base / "pending"
        self.root.mkdir()
        self.pending.mkdir()
        for name in publisher.COMPONENTS:
            (self.root / name).mkdir()
            (self.pending / name).mkdir()
            (self.root / name / "payload").write_text("OLD-" + name)
            (self.pending / name / "payload").write_text("NEW-" + name)

    def assert_originals(self):
        for name in publisher.COMPONENTS:
            self.assertEqual((self.root / name / "payload").read_text(), "OLD-" + name)
        self.assertFalse((self.root / ".publish-backup").exists())

    def test_backup_before_promote(self):
        with self.assertRaises(SystemExit):
            publisher.publish(self.root, self.pending, crash_after=1)
        self.assertEqual((self.root / ".publish-backup" / "dist" / "payload").read_text(), "OLD-dist")
        self.assertFalse((self.root / "dist").exists())
        publisher.recover(self.root)
        self.assert_originals()

    def test_reverse_order_rollback(self):
        with self.assertRaisesRegex(RuntimeError, "INJECTED_FAILURE"):
            publisher.publish(self.root, self.pending, fail_after=8)
        self.assert_originals()

    def test_backup_recovery(self):
        with self.assertRaises(SystemExit):
            publisher.publish(self.root, self.pending, crash_after=1)
        backup = self.root / ".publish-backup" / "dist" / "payload"
        backup.write_text("TAMPERED")
        with self.assertRaisesRegex(RuntimeError, "Corrupted backup"):
            publisher.recover(self.root)
        self.assertTrue(backup.exists())

    def test_no_overwrite_existing_backup(self):
        backup = self.root / ".publish-backup"
        backup.mkdir()
        (backup / "sentinel").write_text("PRESERVE")
        with self.assertRaisesRegex(RuntimeError, "Unresolved"):
            publisher.publish(self.root, self.pending)
        self.assertEqual((backup / "sentinel").read_text(), "PRESERVE")

    def test_sha_before_promotion(self):
        code = SCRIPT.read_text(encoding="utf-8")
        self.assertLess(code.index("Publication alteree:"), code.index("'publish-transaction.py'"))
        self.assertIn("Get-FileHash", code)


if __name__ == "__main__":
    unittest.main()
