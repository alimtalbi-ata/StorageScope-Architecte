"""Fail-closed extraction of a single failed unittest invocation from CI job logs.

The normal parser still rejects trailing wrapper output. This adapter is explicit,
bounds one invocation, and refuses ambiguous or post-summary test records.
Author: Abdelhalim Talbi.
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tools.classify_windows_regression_log import (
    extract_failed_unittest_block_from_job_log,
    main,
    parse_unittest_log,
)


def failed_job_log(tail: str = "##[error]Process completed with exit code 1.") -> str:
    return "\n".join([
        "2026-10-21T20:17:00.0000000Z ##[group]Run historical suite",
        "2026-10-21T20:17:00.1000000Z ERROR: test_missing (sample.Test.test_missing)",
        "2026-10-21T20:17:00.1100000Z Traceback (most recent call last):",
        "2026-10-21T20:17:00.1200000Z ModuleNotFoundError: No module named 'missing_dependency'",
        "2026-10-21T20:17:00.2000000Z Ran 1 test in 0.01s",
        "2026-10-21T20:17:00.2100000Z FAILED (errors=1)",
        "2026-10-21T20:17:00.2200000Z " + tail,
        "",
    ])


class HistoricalJobLogExtractionV6241(unittest.TestCase):
    def test_explicit_extraction_preserves_strict_inner_summary(self):
        full_log = failed_job_log()
        _, strict_summary = parse_unittest_log(full_log)
        self.assertFalse(strict_summary["counts_match_summary"])
        self.assertGreater(strict_summary["trailing_output_lines"], 0)

        block, bounds = extract_failed_unittest_block_from_job_log(full_log)
        entries, summary = parse_unittest_log(block, expected_tests=1)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["category"], "IMPORT_ROOT_OR_SOURCE_PATH")
        self.assertTrue(summary["summary_complete"])
        self.assertTrue(summary["counts_match_summary"])
        self.assertEqual(bounds["mode"], "explicit_failed_unittest_block")
        self.assertEqual(bounds["test_records"], 1)
        self.assertNotIn("Process completed", block)

    def test_full_log_cli_writes_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log_path = root / "job.log"
            json_path = root / "report.json"
            markdown_path = root / "report.md"
            log_path.write_text(failed_job_log(), encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = main([
                    str(log_path),
                    "--extract-failed-unittest-block",
                    "--expected-tests", "1",
                    "--json-output", str(json_path),
                    "--markdown-output", str(markdown_path),
                ])
            self.assertEqual(code, 0, stderr.getvalue())
            report = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(report["summary"]["input_scope"], "github_actions_job_log")
            self.assertEqual(report["summary"]["extraction"]["source_line_start"], 2)
            self.assertEqual(report["summary"]["expected_tests"], 1)
            self.assertIn("Portee entree", markdown_path.read_text(encoding="utf-8"))

    def test_multiple_invocations_fail_closed(self):
        log = failed_job_log() + (
            "2026-10-21T20:17:01.0000000Z Ran 1 test in 0.01s\n"
            "2026-10-21T20:17:01.0100000Z OK\n"
        )
        with self.assertRaisesRegex(ValueError, "exactly one unittest run summary"):
            extract_failed_unittest_block_from_job_log(log)

    def test_post_summary_test_record_fails_closed(self):
        log = failed_job_log("ERROR: forged.Test.extra")
        with self.assertRaisesRegex(ValueError, "record found after terminal summary"):
            extract_failed_unittest_block_from_job_log(log)

    def test_successful_or_recordless_job_log_is_not_extracted(self):
        success = (
            "Ran 1 test in 0.01s\n"
            "OK\n"
            "Build completed"
        )
        with self.assertRaisesRegex(ValueError, "reserved for failed unittest runs"):
            extract_failed_unittest_block_from_job_log(success)
        recordless = "Ran 1 test in 0.01s\nFAILED (errors=1)"
        with self.assertRaisesRegex(ValueError, "no unittest FAIL/ERROR records"):
            extract_failed_unittest_block_from_job_log(recordless)

    def test_expected_test_count_mismatch_keeps_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log_path = root / "job.log"
            json_path = root / "report.json"
            log_path.write_text(failed_job_log(), encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = main([
                    str(log_path),
                    "--extract-failed-unittest-block",
                    "--expected-tests", "958",
                    "--json-output", str(json_path),
                ])
            self.assertEqual(code, 1)
            report = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertFalse(report["summary"]["counts_match_summary"])
            self.assertFalse(report["summary"]["expected_tests_match"])
            self.assertIn("expected count 958", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
