"""V6.250 regression tests for duplicate JSON keys in backup manifests.
Author: Abdelhalim Talbi.
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "03-Sources" / "storagescope_windows.py"
SPEC = importlib.util.spec_from_file_location("storagescope_windows_v6250", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

PAYLOAD = b"storage-scope-backup-proof"
DIGEST = hashlib.sha256(PAYLOAD).hexdigest()
BAD_DIGEST = "0" * 64
CREATED = "2026-10-26T00:00:00+00:00"


def make_manifest(files):
    return {
        "format": "storagescope-backup-v1",
        "created_utc": CREATED,
        "author": "Abdelhalim Talbi",
        "files": files,
    }


class BackupManifestDuplicateKeyQuarantineV6250(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / "snapshot"
        self.folder.mkdir()
        (self.folder / "data.bin").write_bytes(PAYLOAD)

    def write_raw_manifest(self, raw):
        (self.folder / "manifest.json").write_text(raw + "\n", encoding="utf-8")

    def valid_entry_json(self):
        return (
            '{"name":"data.bin","bytes":' + str(len(PAYLOAD))
            + ',"sha256":"' + DIGEST + '"}'
        )

    def test_unique_manifest_remains_valid(self):
        self.write_raw_manifest(json.dumps(make_manifest([{
            "name": "data.bin", "bytes": len(PAYLOAD), "sha256": DIGEST
        }])))
        self.assertTrue(MODULE.verify_backup_snapshot(self.folder))

    def test_duplicate_top_level_format_is_rejected(self):
        raw = (
            '{"format":"wrong","format":"storagescope-backup-v1",'
            + '"created_utc":"' + CREATED + '","author":"Abdelhalim Talbi",'
            + '"files":[' + self.valid_entry_json() + ']}'
        )
        self.write_raw_manifest(raw)
        self.assertFalse(MODULE.verify_backup_snapshot(self.folder))

    def test_duplicate_files_member_is_rejected(self):
        raw = (
            '{"format":"storagescope-backup-v1",'
            + '"created_utc":"' + CREATED + '","author":"Abdelhalim Talbi",'
            + '"files":[],"files":[' + self.valid_entry_json() + ']}'
        )
        self.write_raw_manifest(raw)
        self.assertFalse(MODULE.verify_backup_snapshot(self.folder))

    def test_duplicate_nested_sha256_is_rejected(self):
        entry = (
            '{"name":"data.bin","bytes":' + str(len(PAYLOAD))
            + ',"sha256":"' + BAD_DIGEST + '","sha256":"' + DIGEST + '"}'
        )
        raw = (
            '{"format":"storagescope-backup-v1",'
            + '"created_utc":"' + CREATED + '","author":"Abdelhalim Talbi",'
            + '"files":[' + entry + ']}'
        )
        self.write_raw_manifest(raw)
        self.assertFalse(MODULE.verify_backup_snapshot(self.folder))
        self.assertEqual((self.folder / "data.bin").read_bytes(), PAYLOAD,
                         "Validation must not modify backup bytes.")

    def test_duplicate_unknown_member_is_rejected(self):
        raw = (
            '{"format":"storagescope-backup-v1",'
            + '"created_utc":"' + CREATED + '","author":"Abdelhalim Talbi",'
            + '"comment":"first","comment":"second",'
            + '"files":[' + self.valid_entry_json() + ']}'
        )
        self.write_raw_manifest(raw)
        self.assertFalse(MODULE.verify_backup_snapshot(self.folder))

    def test_governance_and_native_windows_workflows_run_this_regression(self):
        for relative in (
            ".github/workflows/governance-review-qualification.yml",
            ".github/workflows/windows-build.yml",
        ):
            workflow = ROOT / relative
            with self.subTest(workflow=relative):
                self.assertIn(
                    "test_backup_manifest_duplicate_key_quarantine_v6250.py",
                    workflow.read_text(encoding="utf-8"),
                )


if __name__ == "__main__":
    unittest.main()
