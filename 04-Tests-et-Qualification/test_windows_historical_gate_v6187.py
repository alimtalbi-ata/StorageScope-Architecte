"""Protect the real Windows historical suite wiring from silent regression.

Author: Abdelhalim Talbi. Static gate checks plus a real fatal-path subprocess;
these tests do not assert that Windows binaries were qualified.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "02-Compilation-Windows" / "build-engine-windows.ps1"
WORKFLOW = ROOT / ".github" / "workflows" / "windows-build.yml"
RUNNER = ROOT / "scripts" / "run_historical_windows_suite.py"


class HistoricalWindowsGate(unittest.TestCase):
    def test_builder_uses_real_historical_runner_before_pyinstaller(self):
        text = BUILDER.read_text(encoding="utf-8-sig")
        self.assertTrue(RUNNER.is_file(), f"Historical runner missing: {RUNNER}")
        self.assertIn("scripts/run_historical_windows_suite.py", text)
        self.assertIn("--minimum-tests', '958'", text)
        self.assertIn("--minimum-nested-tests', '8'", text)
        self.assertIn("historical-suite-report.json", text)
        self.assertIn("$historicalEvidence.status -ne 'PASS'", text)
        self.assertLess(text.index("Invoke-Checked $builder @($historicalRunner"),
                        text.index("Invoke-Checked $builder @('-m','PyInstaller'"))
        self.assertNotIn("Invoke-Checked $builder @('-m','unittest','discover'", text)

    def test_workflow_keeps_diagnostics_on_failure(self):
        text = WORKFLOW.read_text(encoding="utf-8-sig")
        self.assertIn("02-Compilation-Windows/failed-build-logs/*", text)
        self.assertIn("02-Compilation-Windows/build-logs/*", text)
        self.assertIn("name: StorageScope-Windows-DIAGNOSTICS", text)
        self.assertIn("if: always()", text)

    def test_runner_fatal_path_emits_nonpassing_json(self):
        self.assertTrue(RUNNER.is_file())
        with tempfile.TemporaryDirectory(prefix="storagescope-fatal-") as td:
            root = Path(td)
            report = root / "evidence.json"
            result = subprocess.run(
                [sys.executable, str(RUNNER), "--repo", str(root / "nonexistent"),
                 "--report", str(report), "--minimum-tests", "958",
                 "--minimum-nested-tests", "8"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                encoding="utf-8", errors="replace", check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(report.is_file(), result.stderr)
            evidence = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "FAIL")
            self.assertEqual(evidence["qualification"], "tests_only_not_windows_binary")
            self.assertIn("error_type", evidence)

    def test_runner_does_not_weaken_historical_minima(self):
        text = RUNNER.read_text(encoding="utf-8-sig")
        self.assertRegex(text, r"minimum(?:_tests)?: int = 958")
        self.assertIn("minimum_nested: int = 8", text)
        self.assertRegex(text, r"nested_(?:count|executed) >= minimum_nested")
        self.assertRegex(text, r"(?:completed|run)\.returncode == 0")


if __name__ == "__main__":
    unittest.main()
