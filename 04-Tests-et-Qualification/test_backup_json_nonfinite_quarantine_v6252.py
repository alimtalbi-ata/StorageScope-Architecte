"""V6.252 regression tests: reject non-standard JSON numeric constants in backup manifests.
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
SPEC = importlib.util.spec_from_file_location("storagescope_windows_v6252", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

PAYLOAD = b"storage-scope-backup-proof"
DIGEST = hashlib.sha256(PAYLOAD).hexdigest()
CREATED = "2026-10-26T00:00:00+00:00"


class BackupJsonNonFiniteQuarantineV6252(unittest.TestCase):
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

    def raw_manifest_with_metadata(self, metadata_value):
        return (
            '{"format":"storagescope-backup-v1",'
            + '"created_utc":"' + CREATED + '","author":"Abdelhalim Talbi",'
            + '"files":[' + self.valid_entry_json() + '],'
            + '"metadata":{"numeric_hint":' + metadata_value + '}}'
        )

    def test_non_finite_constants_are_rejected_even_in_unknown_nested_metadata(self):
        for literal in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(literal=literal):
                self.write_raw_manifest(self.raw_manifest_with_metadata(literal))
                self.assertFalse(
                    MODULE.verify_backup_snapshot(self.folder),
                    f"Non-standard JSON numeric token {literal} must fail closed.",
                )
                self.assertEqual(
                    (self.folder / "data.bin").read_bytes(),
                    PAYLOAD,
                    "Manifest validation must not modify snapshot payloads.",
                )

    def test_standard_json_values_in_extension_metadata_remain_valid(self):
        self.write_raw_manifest(
            self.raw_manifest_with_metadata('{"flags":[true,false,null],"ratio":2.5}')
        )
        self.assertTrue(MODULE.verify_backup_snapshot(self.folder))

    def test_governance_and_native_windows_workflows_run_this_regression(self):
        for relative in (
            ".github/workflows/governance-review-qualification.yml",
            ".github/workflows/windows-build.yml",
        ):
            workflow = ROOT / relative
            with self.subTest(workflow=relative):
                self.assertIn(
                    "test_backup_json_nonfinite_quarantine_v6252.py",
                    workflow.read_text(encoding="utf-8"),
                )


if __name__ == "__main__":
    unittest.main()
