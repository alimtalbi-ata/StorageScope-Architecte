"""V6.247 tests for fail-closed integrity of historical selector evidence.

These unit tests use temporary synthetic byte streams only to exercise the
validator contract. They do not represent real StorageScope test-run evidence.
Author: Abdelhalim Talbi.
"""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.run_historical_windows_suite import (
    LOW_CONFIDENCE_BASELINE_RECORDS,
    build_low_confidence_closure,
)


class HistoricalSelectorEvidenceIntegrityV6247(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.evidence_dir = Path(self._temp.name)
        self.selectors = list(dict.fromkeys(
            record["selector"] for record in LOW_CONFIDENCE_BASELINE_RECORDS
        ))
        self.runs = self._make_runs()

    def _make_runs(self, selectors=None):
        selectors = self.selectors if selectors is None else selectors
        runs = []
        for index, selector in enumerate(selectors, start=1):
            raw = f"captured selector output {index}: {selector}\n".encode("utf-8")
            log_file = f"selector-{index:02d}.log"
            (self.evidence_dir / log_file).write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            runs.append({
                "test_selectors": [selector],
                "status": "PASS",
                "executed": 1,
                "exit_code": 0,
                "terminal_unittest_summary": {
                    "status": "OK",
                    "summary_complete": True,
                    "tests_run": 1,
                    "failures": 0,
                    "errors": 0,
                    "skipped": 0,
                    "expected_failures": 0,
                    "unexpected_successes": 0,
                },
                "subprocess_output_decoding": {
                    "status": "ACCEPTED",
                    "decoder": "utf-8-strict",
                    "lossy_decoding_used": False,
                    "payload_sha256": digest,
                    "payload_byte_count": len(raw),
                },
                "log_file": log_file,
                "log_sha256": digest,
                "log_bytes": len(raw),
                "log_encoding": "raw_subprocess_bytes",
            })
        return runs

    def test_valid_evidence_requires_all_eight_selectors_and_13_mappings(self):
        result = build_low_confidence_closure(self.runs, self.evidence_dir)
        self.assertEqual(result["current_regression_status"], "PASS")
        self.assertEqual(result["evidence_integrity_status"], "PASS")
        self.assertEqual(result["baseline_failure_records"], 13)
        self.assertEqual(result["unique_current_test_selectors"], 8)
        self.assertEqual(len(result["records"]), 13)
        self.assertEqual(result["validation_issues"], [])
        self.assertFalse(result["root_cause_resolution_proven"])
        self.assertEqual(result["historical_root_cause_linkage"], "NOT_ESTABLISHED")

    def test_skipped_test_cannot_be_reported_as_pass(self):
        self.runs[0]["terminal_unittest_summary"]["skipped"] = 1
        result = build_low_confidence_closure(self.runs, self.evidence_dir)
        self.assertEqual(result["current_regression_status"], "FAIL")
        self.assertEqual(result["selector_status"][self.selectors[0]], "FAIL_OR_NOT_RUN")
        self.assertTrue(any("skipped must be integer zero" in item for item in result["validation_issues"]))

    def test_duplicate_selector_cannot_hide_an_earlier_failure(self):
        failing_duplicate = copy.deepcopy(self.runs[0])
        failing_duplicate["status"] = "FAIL"
        failing_duplicate["exit_code"] = 1
        failing_duplicate["terminal_unittest_summary"]["status"] = "FAILED"
        failing_duplicate["terminal_unittest_summary"]["failures"] = 1
        result = build_low_confidence_closure([failing_duplicate, *self.runs], self.evidence_dir)
        self.assertEqual(result["current_regression_status"], "FAIL")
        self.assertEqual(result["selector_status"][self.selectors[0]], "FAIL_OR_NOT_RUN")
        self.assertTrue(any("duplicate selector evidence rejected" in item for item in result["validation_issues"]))

    def test_one_process_cannot_claim_multiple_selectors(self):
        combined = copy.deepcopy(self.runs[0])
        combined["test_selectors"] = [self.selectors[0], self.selectors[1]]
        result = build_low_confidence_closure([combined, *self.runs[1:]], self.evidence_dir)
        self.assertEqual(result["current_regression_status"], "FAIL")
        self.assertEqual(result["selector_status"][self.selectors[0]], "FAIL_OR_NOT_RUN")
        self.assertTrue(any("exactly one fully qualified selector" in item for item in result["validation_issues"]))

    def test_missing_terminal_summary_fails_closed(self):
        self.runs[0].pop("terminal_unittest_summary")
        result = build_low_confidence_closure(self.runs, self.evidence_dir)
        self.assertEqual(result["current_regression_status"], "FAIL")
        self.assertTrue(any("terminal unittest summary is missing" in item for item in result["validation_issues"]))

    def test_boolean_count_is_not_accepted_as_integer_zero(self):
        self.runs[0]["terminal_unittest_summary"]["errors"] = False
        result = build_low_confidence_closure(self.runs, self.evidence_dir)
        self.assertEqual(result["current_regression_status"], "FAIL")
        self.assertTrue(any("errors must be integer zero" in item for item in result["validation_issues"]))

    def test_tampered_raw_log_fails_sha256_and_byte_count_validation(self):
        path = self.evidence_dir / self.runs[0]["log_file"]
        path.write_bytes(path.read_bytes() + b"tampered")
        result = build_low_confidence_closure(self.runs, self.evidence_dir)
        self.assertEqual(result["current_regression_status"], "FAIL")
        self.assertTrue(any("raw log bytes do not match" in item for item in result["validation_issues"]))

    def test_missing_raw_log_fails_closed(self):
        (self.evidence_dir / self.runs[0]["log_file"]).unlink()
        result = build_low_confidence_closure(self.runs, self.evidence_dir)
        self.assertEqual(result["current_regression_status"], "FAIL")
        self.assertTrue(any("raw log file is missing" in item for item in result["validation_issues"]))

    def test_evidence_directory_is_mandatory(self):
        result = build_low_confidence_closure(self.runs, None)
        self.assertEqual(result["current_regression_status"], "FAIL")
        self.assertTrue(any("evidence directory is required" in item for item in result["validation_issues"]))

    def test_unsafe_log_path_is_rejected(self):
        self.runs[0]["log_file"] = "../outside.log"
        result = build_low_confidence_closure(self.runs, self.evidence_dir)
        self.assertEqual(result["current_regression_status"], "FAIL")
        self.assertTrue(any("file name is missing or unsafe" in item for item in result["validation_issues"]))


if __name__ == "__main__":
    unittest.main()
