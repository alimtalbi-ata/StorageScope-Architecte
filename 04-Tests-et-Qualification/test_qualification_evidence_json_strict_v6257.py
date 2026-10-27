"""V6.257: strict JSON parsing for native qualification evidence.
The qualification gate must not accept ambiguous or non-standard JSON as PASS.
Author: Abdelhalim Talbi.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qualification_consolidator",
    ROOT / "02-Compilation-Windows" / "consolidate-qualification.py",
)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class QualificationEvidenceStrictJSONV6257(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="storagescope-v6257-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "07-Manifestes").mkdir()
        (self.root / "07-Manifestes" / "VERSION").write_text("6.99", encoding="utf-8")
        self.base = self.root / "02-Compilation-Windows"
        self.base.mkdir()
        self.native = {
            "version": "6.99",
            "overall": "PASS",
            "checks": [
                {"name": name, "status": "PASS"}
                for name in MOD.REQUIRED_NATIVE_CHECKS
            ],
        }
        self.installer = {
            "version": "6.99",
            "status": "PASS",
            "installed": True,
            "version_checked": True,
            "uninstalled": True,
        }
        self.portable = {
            "version": "6.99",
            "status": "PASS",
            "archive_present": True,
            "extracted": True,
            "version_checked": True,
            "self_test": True,
            "cleanup": True,
        }
        self._save_all()

    def _path(self, report):
        return self.base / MOD.NAMES[report]

    def _save_all(self):
        for name, value in (
            ("native", self.native),
            ("installer", self.installer),
            ("portable", self.portable),
        ):
            self._path(name).write_text(
                json.dumps(value, ensure_ascii=False),
                encoding="utf-8",
            )

    def _write_raw(self, report, raw):
        self._path(report).write_text(raw, encoding="utf-8")

    def test_valid_unique_evidence_still_passes(self):
        result = MOD.consolidate(self.root)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(all(x["status"] == "PASS" for x in result["qualification"].values()))

    def test_duplicate_top_level_native_status_fails_closed(self):
        raw = json.dumps(self.native, separators=(",", ":"))
        marker = '"overall":"PASS"'
        self.assertIn(marker, raw)
        self._write_raw("native", raw.replace(marker, '"overall":"FAIL","overall":"PASS"', 1))
        result = MOD.consolidate(self.root)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["qualification"]["native"]["status"], "FAIL")
        self.assertEqual(result["qualification"]["native"]["reason"], "ValueError")

    def test_duplicate_nested_check_status_fails_closed(self):
        raw = json.dumps(self.native, separators=(",", ":"))
        marker = '"status":"PASS"'
        self.assertIn(marker, raw)
        self._write_raw("native", raw.replace(marker, '"status":"FAIL","status":"PASS"', 1))
        result = MOD.consolidate(self.root)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["qualification"]["native"]["reason"], "ValueError")

    def test_duplicate_installer_status_fails_closed(self):
        raw = json.dumps(self.installer, separators=(",", ":"))
        marker = '"status":"PASS"'
        self.assertIn(marker, raw)
        self._write_raw("installer", raw.replace(marker, '"status":"FAIL","status":"PASS"', 1))
        result = MOD.consolidate(self.root)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["qualification"]["installer"]["reason"], "ValueError")

    def test_non_standard_constant_in_ignored_extension_fails_closed(self):
        raw = json.dumps(self.portable, separators=(",", ":"))
        self._write_raw("portable", raw[:-1] + ',"diagnostic":{"ratio":NaN}}')
        result = MOD.consolidate(self.root)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["qualification"]["portable"]["reason"], "ValueError")

    def test_invalid_utf8_evidence_fails_closed(self):
        path = self._path("native")
        path.write_bytes(json.dumps(self.native).encode("utf-8") + b"\xff")
        result = MOD.consolidate(self.root)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["qualification"]["native"]["status"], "FAIL")
        self.assertEqual(result["qualification"]["native"]["reason"], "UnicodeDecodeError")

    def test_non_standard_infinity_token_fails_closed(self):
        raw = json.dumps(self.installer, separators=(",", ":"))
        self._write_raw("installer", raw[:-1] + ',"diagnostic":{"rate":Infinity}}')
        result = MOD.consolidate(self.root)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["qualification"]["installer"]["reason"], "ValueError")

    def test_both_release_workflows_execute_this_regression_suite(self):
        windows = (ROOT / ".github" / "workflows" / "windows-build.yml").read_text(encoding="utf-8")
        governance = (ROOT / ".github" / "workflows" / "governance-review-qualification.yml").read_text(encoding="utf-8")
        filename = "test_qualification_evidence_json_strict_v6257.py"
        self.assertEqual(windows.count(filename), 1)
        self.assertEqual(governance.count(filename), 2)
        self.assertIn("test_storage_capacity_json_strict_v6256.py", windows)
        self.assertIn("test_storage_capacity_json_strict_v6256.py", governance)


if __name__ == "__main__":
    unittest.main()
