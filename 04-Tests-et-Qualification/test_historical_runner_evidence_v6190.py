"""Real subprocess evidence tests for the Windows historical runner (v6.190).

Uses isolated synthetic unittest files; never claims native Windows qualification.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_historical_windows_suite.py"
SPEC = importlib.util.spec_from_file_location("storagescope_historical_evidence", SCRIPT)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class HistoricalEvidenceTests(unittest.TestCase):
    def make_checkout(self, base: Path, failing: bool) -> Path:
        repo = base / "checkout"
        for name in ("03-Sources", "02-Compilation-Windows", "04-Tests-et-Qualification"):
            (repo / name).mkdir(parents=True)
        test_code = (
            "import unittest\n"
            "class Smoke(unittest.TestCase):\n"
            + ("    def test_check(self): self.fail('deliberate failure')\n"
               if failing else "    def test_check(self): self.assertEqual(2 + 2, 4)\n")
        )
        (repo / "04-Tests-et-Qualification" / "test_synthetic.py").write_text(
            test_code, encoding="utf-8")
        return repo

    def check_log_integrity(self, result: dict, evidence: Path) -> None:
        row = result["suites"][0]
        path = evidence / row["log_file"]
        self.assertTrue(path.is_file())
        content = path.read_bytes()
        self.assertEqual(len(content), row["log_bytes"])
        self.assertEqual(hashlib.sha256(content).hexdigest(), row["log_sha256"])
        self.assertIn(b"Ran 1 test", content)

    def test_success_persists_real_log_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = self.make_checkout(base, failing=False)
            report = base / "evidence" / "result.json"
            result = RUNNER.execute(repo, minimum_tests=1, minimum_nested=0, report=report)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["status"], "PASS")
            self.check_log_integrity(result, report.parent)

    def test_failure_persists_real_log_and_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = self.make_checkout(base, failing=True)
            report = base / "evidence" / "result.json"
            result = RUNNER.execute(repo, minimum_tests=1, minimum_nested=0, report=report)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["suites"][0]["exit_code"], 1)
            self.assertEqual(result["suites"][0]["symptom_counts"]["assertion_failure"], 1)
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["status"], "FAIL")
            self.check_log_integrity(result, report.parent)
            self.assertIn(b"deliberate failure", (report.parent / result["suites"][0]["log_file"]).read_bytes())


if __name__ == "__main__":
    unittest.main()
