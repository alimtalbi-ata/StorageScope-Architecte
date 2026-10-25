"""Regression tests for authoritative historical-suite outcome evidence.

Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_historical_windows_suite as runner


class HistoricalTerminalSummaryV6239(unittest.TestCase):
    def test_nested_negative_control_does_not_override_terminal_ok(self):
        output = """===== nested negative control =====
======================================================================
FAIL: test_check (test_synthetic.Smoke.test_check)
----------------------------------------------------------------------
AssertionError: deliberate failure
----------------------------------------------------------------------
Ran 1 test in 0.000s
FAILED (failures=1)
===== parent historical suite =====
----------------------------------------------------------------------
Ran 1766 tests in 56.804s
OK
"""
        result = runner.parse_terminal_summary(output)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["tests_run"], 1766)
        self.assertEqual(result["failures"], 0)
        self.assertEqual(result["errors"], 0)
        self.assertTrue(result["summary_complete"])
        self.assertEqual(result["trailing_output_lines"], 0)

    def test_missing_terminal_result_summary_is_incomplete(self):
        result = runner.parse_terminal_summary("Ran 10 tests in 1.2s\n")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertFalse(result["summary_complete"])
        self.assertIn("terminal unittest result summary missing", result["problems"])

    def test_terminal_failed_summary_requires_a_real_count(self):
        result = runner.parse_terminal_summary(
            "Ran 1 test in 0.01s\nFAILED (failures=0, errors=0)\n"
        )
        self.assertEqual(result["status"], "FAILED")
        self.assertFalse(result["summary_complete"])
        self.assertTrue(any("declares no failure" in p for p in result["problems"]))

    def test_unsupported_or_duplicate_ok_fields_are_rejected(self):
        for details in ("skipped=1, skipped=2", "unexpected successes=1", "unknown=1"):
            with self.subTest(details=details):
                result = runner.parse_terminal_summary(
                    f"Ran 2 tests in 0.01s\nOK ({details})\n"
                )
                self.assertFalse(result["summary_complete"])

    def test_result_marker_requires_full_schema_and_terminal_position(self):
        payload = {
            "status": "OK", "tests_run": 1, "failures": 0, "errors": 0,
            "skipped": 0, "expected_failures": 0, "unexpected_successes": 0,
        }
        token = "test-parent-token"
        marker = f"{runner.RUNNER_RESULT_PREFIX}{token}: " + json.dumps(payload)
        self.assertTrue(runner.parse_terminal_summary(marker, expected_token=token)["summary_complete"])
        for output in (
            marker + "\nlate diagnostic",
            marker + "\n" + marker,
            f"{runner.RUNNER_RESULT_PREFIX}{token}: " + '{"status":"OK","tests_run":1}',
        ):
            with self.subTest(output=output):
                parsed = runner.parse_terminal_summary(output, expected_token=token)
                self.assertFalse(parsed["summary_complete"])
                self.assertTrue(parsed["problems"])

    def test_child_marker_cannot_satisfy_parent_invocation(self):
        child_payload = {
            "status": "OK", "tests_run": 1, "failures": 0, "errors": 0,
            "skipped": 0, "expected_failures": 0, "unexpected_successes": 0,
        }
        child_marker = f"{runner.RUNNER_RESULT_PREFIX}child-token: " + json.dumps(child_payload)
        parent = runner.parse_terminal_summary(
            child_marker + "\nRan 1 test in 0.01s\nOK\n",
            expected_token="parent-token",
        )
        self.assertEqual(parent["status"], "UNKNOWN")
        self.assertFalse(parent["summary_complete"])
        self.assertTrue(any("nested/foreign" in item for item in parent["problems"]))

    def test_real_subprocess_keeps_nested_failure_as_diagnostic_not_outcome(self):
        with tempfile.TemporaryDirectory(prefix="storagescope-v6239-") as tmp:
            root = Path(tmp)
            tests = root / "tests"
            tests.mkdir()
            scripts = root / "scripts"
            scripts.mkdir()
            shutil.copy2(ROOT / "scripts" / "unittest_discover_with_result.py",
                         scripts / "unittest_discover_with_result.py")
            test_code = '''import subprocess, sys, unittest
class NestedControl(unittest.TestCase):
    def test_expected_child_failure(self):
        child = "import unittest\\nclass T(unittest.TestCase):\\n def test_fail(self): self.fail('negative control')\\nunittest.main()"
        result = subprocess.run([sys.executable, '-c', child], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(result.stdout)
        self.assertEqual(result.returncode, 1)
'''
            (tests / "test_nested_control.py").write_text(test_code, encoding="utf-8")
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            cap = io.StringIO()
            with contextlib.redirect_stdout(cap):
                result = runner.run_suite(tests, "test_*.py", root, env, 1, "nested-control")
            self.assertEqual(result["status"], "PASS", msg=f"result={result!r}\noutput={cap.getvalue()}")
            self.assertEqual(result["terminal_unittest_summary"]["status"], "OK")
            self.assertEqual(result["terminal_unittest_summary"]["failures"], 0)
            self.assertEqual(result["terminal_unittest_summary"]["errors"], 0)
            self.assertEqual(result["captured_output_symptom_counts"].get("assertion_failure"), 1)
            self.assertIn("nested unittest runs and intentional negative controls", result["symptom_counts_scope"])


if __name__ == "__main__":
    unittest.main()
