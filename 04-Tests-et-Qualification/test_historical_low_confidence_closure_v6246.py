"""V6.246 closure gate for the 13 low-confidence records from run #39668811238.

This test proves coverage and fail-closed reporting, not historical root-cause
attribution. Author: Abdelhalim Talbi.
"""
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.run_historical_windows_suite import LOW_CONFIDENCE_BASELINE_RECORDS, build_low_confidence_closure

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "04-Tests-et-Qualification"


class HistoricalLowConfidenceClosureV6246(unittest.TestCase):
    def _valid_selector_runs(self, evidence_dir, selectors=None):
        evidence_dir.mkdir(parents=True, exist_ok=True)
        if selectors is None:
            selectors = list(dict.fromkeys(r["selector"] for r in LOW_CONFIDENCE_BASELINE_RECORDS))
        runs = []
        for index, selector in enumerate(selectors, start=1):
            raw = f"selector test output {index}: {selector}\n".encode("utf-8")
            log_name = f"selector-{index:02d}.log"
            (evidence_dir / log_name).write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            runs.append({
                "test_selectors": [selector],
                "status": "PASS",
                "executed": 1,
                "exit_code": 0,
                "terminal_unittest_summary": {
                    "status": "OK", "summary_complete": True, "tests_run": 1,
                    "failures": 0, "errors": 0, "skipped": 0,
                    "expected_failures": 0, "unexpected_successes": 0,
                },
                "subprocess_output_decoding": {
                    "status": "ACCEPTED", "decoder": "utf-8-strict",
                    "lossy_decoding_used": False, "payload_sha256": digest,
                    "payload_byte_count": len(raw),
                },
                "log_file": log_name, "log_sha256": digest,
                "log_bytes": len(raw), "log_encoding": "raw_subprocess_bytes",
            })
        return runs
    def test_thirteen_records_match_the_immutable_baseline_taxonomy(self):
        taxonomy = json.loads((TESTS / "windows-historical-failure-taxonomy-v39668811238.json").read_text(encoding="utf-8"))
        self.assertEqual({r["taxonomy_key"] for r in LOW_CONFIDENCE_BASELINE_RECORDS},
                         set(taxonomy["classification"]["manual_follow_up_tests"]))
        self.assertEqual(len(LOW_CONFIDENCE_BASELINE_RECORDS), 13)
        self.assertEqual(taxonomy["run_id"], 39668811238)
        self.assertEqual(taxonomy["suite"]["tests_run"], 958)
        self.assertEqual(taxonomy["suite"]["failures"], 52)
        self.assertEqual(taxonomy["suite"]["errors"], 173)
        self.assertTrue(taxonomy["classification"]["is_heuristic"])

    def test_eight_unique_current_selectors_resolve_to_real_test_methods(self):
        selectors = list(dict.fromkeys(r["selector"] for r in LOW_CONFIDENCE_BASELINE_RECORDS))
        self.assertEqual(len(selectors), 8)
        for selector in selectors:
            with self.subTest(selector=selector):
                module, class_name, method_name = selector.split(".")
                path = TESTS / f"{module}.py"
                self.assertTrue(path.is_file(), path)
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name]
                self.assertEqual(len(classes), 1)
                methods = [n.name for n in classes[0].body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                self.assertIn(method_name, methods)

    def test_six_bootstrap_records_share_named_subTests(self):
        records = [r for r in LOW_CONFIDENCE_BASELINE_RECORDS if r["id"] in {"LC-003","LC-004","LC-005","LC-006","LC-007","LC-008"}]
        self.assertEqual(len(records), 6)
        self.assertEqual(len({r["selector"] for r in records}), 1)
        path = TESTS / "test_release_package_v615.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        literals = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        self.assertTrue({r["subtest"] for r in records}.issubset(literals))
        self.assertTrue(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "subTest" for n in ast.walk(tree)))

    def test_all_current_selectors_pass_without_proving_historical_root_cause(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence_dir = Path(temp)
            runs = self._valid_selector_runs(evidence_dir)
            result = build_low_confidence_closure(runs, evidence_dir)
        self.assertEqual(result["current_regression_status"], "PASS")
        self.assertEqual(result["evidence_integrity_status"], "PASS")
        self.assertEqual(len(result["records"]), 13)
        self.assertTrue(all(r["current_test_status"] == "PASS" for r in result["records"]))
        self.assertTrue(all(r["root_cause_resolution_proven"] is False for r in result["records"]))
        self.assertEqual(result["historical_root_cause_linkage"], "NOT_ESTABLISHED")
        self.assertEqual(result["validation_issues"], [])

    def test_failure_of_shared_bootstrap_selector_marks_six_records_failed(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence_dir = Path(temp)
            runs = self._valid_selector_runs(evidence_dir)
            shared = "test_release_package_v615.TestReleaseV615.test_bootstrap_files_exist"
            runs = [dict(r, status="FAIL", exit_code=1) if shared in r["test_selectors"] else r for r in runs]
            result = build_low_confidence_closure(runs, evidence_dir)
        failed = {r["id"] for r in result["records"] if r["current_test_status"] != "PASS"}
        self.assertEqual(failed, {"LC-003","LC-004","LC-005","LC-006","LC-007","LC-008"})
        self.assertEqual(result["current_regression_status"], "FAIL")

    def test_missing_selector_evidence_fails_closed(self):
        selectors = list(dict.fromkeys(r["selector"] for r in LOW_CONFIDENCE_BASELINE_RECORDS))
        with tempfile.TemporaryDirectory() as temp:
            evidence_dir = Path(temp)
            runs = self._valid_selector_runs(evidence_dir, selectors[:-1])
            result = build_low_confidence_closure(runs, evidence_dir)
        self.assertEqual(result["current_regression_status"], "FAIL")
        self.assertTrue(any(r["current_test_status"] == "FAIL_OR_NOT_RUN" for r in result["records"]))
        self.assertTrue(any("missing selector evidence" in item for item in result["validation_issues"]))


if __name__ == "__main__":
    unittest.main()
