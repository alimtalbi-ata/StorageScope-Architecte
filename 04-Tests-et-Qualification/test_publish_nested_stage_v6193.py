"""Regression for native build's nested, named transaction staging.

Author: Abdelhalim Talbi. Uses only temporary directories and real filesystem
renames; no production publication or deployment.
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "02-Compilation-Windows/publish-transaction.py"
spec = importlib.util.spec_from_file_location("storagescope_publisher_nested", MODULE)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class NestedPublicationContract(unittest.TestCase):
    def setup_paths(self, base, stage_name=".publish-pending"):
        root = base / "release"
        root.mkdir()
        (root / "dist").mkdir()
        (root / "dist/StorageScope.exe").write_bytes(b"old")
        pending = root / stage_name
        (pending / "dist").mkdir(parents=True)
        (pending / "dist/StorageScope.exe").write_bytes(b"new")
        return root, pending

    def test_named_child_publishes_and_removes_empty_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, pending = self.setup_paths(Path(tmp))
            publisher.publish(root, pending)
            self.assertEqual((root / "dist/StorageScope.exe").read_bytes(), b"new")
            self.assertFalse(pending.exists())
            self.assertFalse((root / ".publish-backup").exists())

    def test_arbitrary_nested_path_rejected_without_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, pending = self.setup_paths(Path(tmp), "arbitrary-stage")
            with self.assertRaisesRegex(ValueError, "separate directories"):
                publisher.publish(root, pending)
            self.assertEqual((root / "dist/StorageScope.exe").read_bytes(), b"old")
            self.assertTrue(pending.exists())

    def test_extra_nested_staging_contents_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, pending = self.setup_paths(Path(tmp))
            (pending / "unreviewed.txt").write_text("unexpected")
            with self.assertRaisesRegex(ValueError, "Unexpected nested staging"):
                publisher.publish(root, pending)
            self.assertEqual((root / "dist/StorageScope.exe").read_bytes(), b"old")
            self.assertFalse((root / ".publish-backup").exists())

    def test_injected_failure_restores_old_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, pending = self.setup_paths(Path(tmp))
            with self.assertRaisesRegex(RuntimeError, "INJECTED_FAILURE"):
                publisher.publish(root, pending, fail_after=2)
            self.assertEqual((root / "dist/StorageScope.exe").read_bytes(), b"old")
            self.assertFalse((root / ".publish-backup").exists())


if __name__ == "__main__":
    unittest.main()
