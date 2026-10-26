"""V6.249 regression tests for snapshot directory path boundaries.

Verifies real snapshot directories, root and ancestor symlinks, and Windows
junction detection. The rejection path must happen before opening the manifest.
Author: Abdelhalim Talbi.
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "03-Sources" / "storagescope_windows.py"
import importlib.util

SPEC = importlib.util.spec_from_file_location("storagescope_windows_v6249", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def make_snapshot(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    payload = b"storage-scope-backup-proof"
    (folder / "data.bin").write_bytes(payload)
    manifest = {
        "format": "storagescope-backup-v1",
        "created_utc": "2026-10-26T00:00:00+00:00",
        "author": "Abdelhalim Talbi",
        "files": [{
            "name": "data.bin",
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }],
    }
    (folder / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8"
    )
    return folder


class BackupRootLinkQuarantineV6249(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.snapshot = make_snapshot(self.base / "real" / "snapshot")

    def test_regular_snapshot_remains_valid(self):
        self.assertTrue(MODULE.verify_backup_snapshot(self.snapshot))

    def test_snapshot_root_symlink_is_rejected_before_manifest_read(self):
        link = self.base / "snapshot-link"
        try:
            link.symlink_to(self.snapshot, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"directory symlink unavailable in this environment: {exc}")
        with patch.object(Path, "read_text", side_effect=AssertionError(
            "manifest must not be opened through a linked root"
        )):
            self.assertFalse(MODULE.verify_backup_snapshot(link))

    def test_symlinked_ancestor_is_rejected_before_manifest_read(self):
        alias = self.base / "alias"
        try:
            alias.symlink_to(self.snapshot.parent, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"directory symlink unavailable in this environment: {exc}")
        candidate = alias / self.snapshot.name
        with patch.object(Path, "read_text", side_effect=AssertionError(
            "manifest must not be opened through a linked ancestor"
        )):
            self.assertFalse(MODULE.verify_backup_snapshot(candidate))

    def test_symlink_component_before_dotdot_is_rejected(self):
        alias = self.base / "alias"
        try:
            alias.symlink_to(self.snapshot.parent, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"directory symlink unavailable in this environment: {exc}")
        # OS path traversal through alias/.. arrives at the same snapshot, but the
        # untrusted caller path still crossed a symbolic-link component. Fail closed.
        candidate = alias / ".." / self.snapshot.parent.name / self.snapshot.name
        self.assertTrue(candidate.is_dir())
        with patch.object(Path, "read_text", side_effect=AssertionError(
            "manifest must not be opened after a linked path component"
        )):
            self.assertFalse(MODULE.verify_backup_snapshot(candidate))

    def test_windows_junction_component_is_rejected(self):
        candidate = self.base / "junction" / "snapshot"
        if not hasattr(Path, "is_junction"):
            self.skipTest("pathlib.Path.is_junction requires Python 3.12+")
        with patch.object(Path, "is_symlink", autospec=True, return_value=False):
            with patch.object(
                Path, "is_junction", autospec=True,
                side_effect=lambda path: path == candidate.parent,
            ):
                self.assertTrue(MODULE._snapshot_path_has_link_component(candidate))

    def test_regular_file_is_not_a_snapshot_root(self):
        file_path = self.base / "not-a-directory"
        file_path.write_text("not a directory", encoding="utf-8")
        self.assertFalse(MODULE.verify_backup_snapshot(file_path))

    def test_both_qualification_workflows_run_this_regression(self):
        workflows = (
            ROOT / ".github" / "workflows" / "governance-review-qualification.yml",
            ROOT / ".github" / "workflows" / "windows-build.yml",
        )
        for workflow in workflows:
            with self.subTest(workflow=workflow.name):
                text = workflow.read_text(encoding="utf-8")
                self.assertIn(
                    "test_backup_root_link_quarantine_v6249.py",
                    text,
                    f"{workflow.name} must run the V6.249 regression explicitly",
                )


if __name__ == "__main__":
    unittest.main()
