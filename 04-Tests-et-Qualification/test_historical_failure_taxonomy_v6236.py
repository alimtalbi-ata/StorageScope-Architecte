"""Regression tests for Windows historical failure log taxonomy. Author: Abdelhalim Talbi."""
import unittest

from tools.classify_windows_regression_log import (
    classify_failure,
    make_report,
    parse_unittest_log,
    render_markdown,
)


class HistoricalFailureTaxonomyV6236(unittest.TestCase):
    def test_extracts_failures_errors_and_summary_without_losing_names(self):
        log = """2026-10-21T20:17:00Z ERROR: test_import (test_sample.TestSample.test_import)
Traceback (most recent call last):
ModuleNotFoundError: No module named 'governance'
2026-10-21T20:17:01Z FAIL: test_version (test_sample.TestSample.test_version)
Traceback (most recent call last):
AssertionError: '6.108' != '6.87'
Ran 2 tests in 0.02s
FAILED (failures=1, errors=1)
"""
        entries, summary = parse_unittest_log(log)
        self.assertEqual([e["kind"] for e in entries], ["ERROR", "FAIL"])
        self.assertEqual(entries[0]["test"], "test_import (test_sample.TestSample.test_import)")
        self.assertEqual(entries[0]["category"], "IMPORT_ROOT_OR_SOURCE_PATH")
        self.assertEqual(entries[1]["category"], "STALE_VERSION_EXPECTATION")
        self.assertEqual(summary["tests_run"], 2)
        self.assertTrue(summary["counts_match_summary"])

    def test_classifies_windows_root_causes_and_keeps_ambiguous_cases_visible(self):
        cases = [
            ("FileNotFoundError: missing D:/repo/04-Tests-et-Qualification/desktop.py", "TEST_ARBORESCENCE_OR_CWD"),
            ("PermissionError: [WinError 32] database.sqlite", "SQLITE_HANDLE_LIFECYCLE"),
            ("UnicodeDecodeError: 'utf-8' codec can't decode byte", "ENCODING"),
            ("ValueError: substring not found", "STALE_SOURCE_CONTRACT"),
            ("ValueError: Invalid PE section count", "WINDOWS_FIXTURE_OR_EXECUTABLE_STRUCTURE"),
            ("RuntimeError: unknown vendor-specific condition", "OTHER_NEEDS_MANUAL_TRIAGE"),
        ]
        for detail, expected in cases:
            with self.subTest(detail=detail):
                self.assertEqual(classify_failure(detail)[0], expected)

    def test_report_counts_failures_and_errors_by_root_cause(self):
        log = """FAIL: test_a
AssertionError: '6.108' != '6.87'
ERROR: test_b
PermissionError: [WinError 32] database.sqlite
Ran 2 tests in 0.02s
FAILED (failures=1, errors=1)
"""
        entries, summary = parse_unittest_log(log)
        report = make_report(entries, summary, "example", "fixture.log")
        self.assertEqual(sum(c["total"] for c in report["categories"]), 2)
        self.assertEqual(sum(c["failures"] for c in report["categories"]), 1)
        self.assertEqual(sum(c["errors"] for c in report["categories"]), 1)
        self.assertIn("test par test", render_markdown(report))

    def test_refuses_to_claim_encoding_cleanliness_when_a_codec_error_exists(self):
        category, _, _ = classify_failure("UnicodeEncodeError: 'charmap' codec can't encode character")
        self.assertEqual(category, "ENCODING")


if __name__ == "__main__":
    unittest.main()
