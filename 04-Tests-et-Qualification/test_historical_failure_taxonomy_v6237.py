"""Fail-closed summary validation for historical Windows regression logs.
Author: Abdelhalim Talbi.
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tools.classify_windows_regression_log import (
    main,
    make_report,
    parse_unittest_log,
    render_markdown,
)


class HistoricalFailureTaxonomyV6237(unittest.TestCase):
    def test_complete_failure_summary_matches_observed_records(self):
        log = """FAIL: test_one (sample.Test.test_one)
AssertionError: expected value
ERROR: test_two (sample.Test.test_two)
ModuleNotFoundError: No module named 'sample_dependency'
Ran 2 tests in 0.02s
FAILED (failures=1, errors=1)
"""
        entries, summary = parse_unittest_log(log)
        self.assertEqual(len(entries), 2)
        self.assertTrue(summary["summary_present"])
        self.assertTrue(summary["summary_complete"])
        self.assertTrue(summary["counts_match_summary"])
        self.assertEqual(summary["result_status"], "FAILED")
        self.assertEqual(summary["summary_problem"], [])

    def test_missing_final_summary_never_counts_as_consistent(self):
        entries, summary = parse_unittest_log(
            "FAIL: test_one (sample.Test.test_one)\nAssertionError: expected value\n"
        )
        self.assertEqual(len(entries), 1)
        self.assertFalse(summary["summary_present"])
        self.assertFalse(summary["summary_complete"])
        self.assertFalse(summary["counts_match_summary"])
        self.assertIn("missing Ran <n> tests summary", summary["summary_problem"])
        self.assertIn("missing final OK/FAILED summary", summary["summary_problem"])

    def test_declared_failure_and_error_totals_must_match_records(self):
        log = """FAIL: test_one (sample.Test.test_one)
AssertionError: expected value
ERROR: test_two (sample.Test.test_two)
ModuleNotFoundError: No module named 'sample_dependency'
Ran 2 tests in 0.02s
FAILED (failures=1, errors=0)
"""
        _, summary = parse_unittest_log(log)
        self.assertTrue(summary["summary_complete"])
        self.assertFalse(summary["counts_match_summary"])
        self.assertTrue(any("totals do not match" in item for item in summary["summary_problem"]))

    def test_multiple_test_runs_in_one_input_are_rejected_as_ambiguous(self):
        log = """FAIL: test_one (sample.Test.test_one)
AssertionError: expected value
Ran 1 test in 0.01s
FAILED (failures=1, errors=0)
Ran 1 test in 0.01s
OK
"""
        _, summary = parse_unittest_log(log)
        self.assertFalse(summary["summary_complete"])
        self.assertFalse(summary["counts_match_summary"])
        self.assertTrue(any("exactly one unittest run summary" in item for item in summary["summary_problem"]))
        self.assertTrue(any("exactly one unittest result summary" in item for item in summary["summary_problem"]))

    def test_known_historical_test_count_can_be_enforced(self):
        log = """FAIL: test_one (sample.Test.test_one)
AssertionError: expected value
Ran 1 test in 0.01s
FAILED (failures=1, errors=0)
"""
        _, summary = parse_unittest_log(log, expected_tests=958)
        self.assertFalse(summary["expected_tests_match"])
        self.assertFalse(summary["counts_match_summary"])
        self.assertIn("declared test count does not match expected count 958", summary["summary_problem"])

    def test_report_and_markdown_expose_incomplete_summary(self):
        entries, summary = parse_unittest_log(
            "ERROR: test_one (sample.Test.test_one)\nRuntimeError: broken test\n"
        )
        report = make_report(entries, summary, "sample-run", "truncated.log")
        markdown = render_markdown(report)
        self.assertFalse(report["summary"]["counts_match_summary"])
        self.assertIn("Résumé présent/complet", markdown)
        self.assertIn("missing final OK/FAILED summary", markdown)

    def test_cli_returns_nonzero_and_writes_report_for_truncated_log(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log_path = root / "truncated.log"
            json_path = root / "report.json"
            log_path.write_text(
                "FAIL: test_one (sample.Test.test_one)\nAssertionError: broken\n",
                encoding="utf-8",
            )
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = main([str(log_path), "--json-output", str(json_path), "--expected-tests", "958"])
            self.assertEqual(code, 1)
            self.assertTrue(json_path.is_file())
            report = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertFalse(report["summary"]["counts_match_summary"])
            self.assertIn("refusing to qualify", stderr.getvalue())


    def test_duplicate_failure_count_fields_are_rejected(self):
        log = """FAIL: test_one (sample.Test.test_one)
AssertionError: expected value
Ran 1 test in 0.01s
FAILED (failures=1, errors=0, failures=1)
"""
        _, summary = parse_unittest_log(log)
        self.assertFalse(summary["summary_complete"])
        self.assertFalse(summary["counts_match_summary"])
        self.assertIn(
            "FAILED summary contains duplicate count fields",
            summary["summary_problem"],
        )

    def test_trailing_garbage_after_run_summary_is_rejected(self):
        log = """FAIL: test_one (sample.Test.test_one)
AssertionError: expected value
Ran 1 test in 0.01s trailing-data
FAILED (failures=1, errors=0)
"""
        _, summary = parse_unittest_log(log)
        self.assertFalse(summary["summary_complete"])
        self.assertFalse(summary["counts_match_summary"])
        self.assertIn("missing Ran <n> tests summary", summary["summary_problem"])



    def test_failed_summary_with_zero_failure_and_error_counts_is_rejected(self):
        log = """Ran 1 test in 0.01s
FAILED (failures=0, errors=0)
"""
        _, summary = parse_unittest_log(log)
        self.assertFalse(summary["summary_complete"])
        self.assertFalse(summary["counts_match_summary"])
        self.assertIn(
            "FAILED summary declares zero failures and errors",
            summary["summary_problem"],
        )

    def test_nonempty_output_after_final_summary_is_rejected(self):
        log = """Ran 1 test in 0.01s
OK
Build step: artifact upload failed
"""
        _, summary = parse_unittest_log(log)
        self.assertEqual(summary["trailing_output_lines"], 1)
        self.assertFalse(summary["summary_complete"])
        self.assertFalse(summary["counts_match_summary"])
        self.assertTrue(any(
            "unexpected non-empty output after unittest result summary" in item
            for item in summary["summary_problem"]
        ))


    def test_malformed_run_summary_after_ok_is_rejected(self):
        log = """Ran 1 test in 0.01s
OK
Ran 99 tests in ???s
"""
        _, summary = parse_unittest_log(log)
        self.assertEqual(summary["trailing_output_lines"], 1)
        self.assertFalse(summary["summary_complete"])
        self.assertFalse(summary["counts_match_summary"])

    def test_ok_summary_payload_must_match_supported_unittest_fields(self):
        for payload in ("nonsense", "skipped=1, skipped=2", "unexpected successes=1"):
            with self.subTest(payload=payload):
                _, summary = parse_unittest_log(
                    "Ran 1 test in 0.01s\nOK (" + payload + ")\n"
                )
                self.assertFalse(summary["summary_complete"])
                self.assertFalse(summary["counts_match_summary"])

    def test_standard_unittest_skipped_and_expected_failure_payload_is_accepted(self):
        _, summary = parse_unittest_log(
            "Ran 2 tests in 0.01s\nOK (skipped=1, expected failures=1)\n"
        )
        self.assertTrue(summary["summary_complete"])
        self.assertTrue(summary["counts_match_summary"])

if __name__ == "__main__":
    unittest.main()
