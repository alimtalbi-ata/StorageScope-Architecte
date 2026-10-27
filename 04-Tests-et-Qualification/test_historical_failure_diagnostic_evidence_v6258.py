"""V6.258 regression coverage for bounded historical failure diagnostics.

The test fixtures are synthetic parser inputs, not historical-run evidence.
Author: Abdelhalim Talbi.
"""
import hashlib
import unittest

from tools.classify_windows_regression_log import (
    build_bounded_diagnostics,
    make_report,
    parse_unittest_log,
    render_markdown,
)


class HistoricalFailureDiagnosticEvidenceV6258(unittest.TestCase):
    def _report(self, detail):
        log = (
            "ERROR: test_import (sample.Test.test_import)\n"
            + detail
            + "\nRan 1 test in 0.01s\nFAILED (errors=1)\n"
        )
        entries, summary = parse_unittest_log(log, expected_tests=1)
        self.assertTrue(summary["counts_match_summary"], summary["summary_problem"])
        return make_report(entries, summary, "synthetic-test", "synthetic.log")

    def test_report_contains_exception_and_repository_relative_frame_without_raw_detail(self):
        detail = (
            'Traceback (most recent call last):\n'
            '  File "D:\\a\\StorageScope-Architecte\\StorageScope-Architecte\\'
            '04-Tests-et-Qualification\\test_sample.py", line 42, in test_import\n'
            "    raise ModuleNotFoundError('example_module')\n"
            "ModuleNotFoundError: No module named 'example_module'"
        )
        report = self._report(detail)
        item = report["items"][0]
        evidence = item["diagnostics"]
        self.assertEqual(report["schema"], "storagescope.windows-historical-failure-taxonomy.v2")
        self.assertEqual(evidence["exception_type"], "ModuleNotFoundError")
        self.assertEqual(evidence["exception_message"], "No module named 'example_module'")
        self.assertEqual(
            evidence["traceback_frames"][0],
            {
                "file": "04-Tests-et-Qualification/test_sample.py",
                "line": 42,
                "function": "test_import",
            },
        )
        self.assertNotIn("detail", item)
        self.assertFalse(evidence["raw_detail_retained"])
        normalized_detail = "\n".join(line.strip() for line in detail.splitlines())
        self.assertEqual(evidence["detail_sha256"], hashlib.sha256(normalized_detail.encode("utf-8")).hexdigest())
        self.assertTrue(report["classification_is_heuristic"])
        self.assertEqual(report["summary"]["tests_run"], 1)

    def test_diagnostic_message_redacts_credentials_and_absolute_paths(self):
        token = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"
        detail = (
            "RuntimeError: failed at D:\\a\\StorageScope-Architecte\\private\\file.py "
            "token=abc123 password=do-not-store " + token
        )
        evidence = build_bounded_diagnostics(detail)
        displayed = evidence["exception_message"]
        for sensitive in (token, "abc123", "do-not-store", "D:\\a\\StorageScope-Architecte"):
            self.assertNotIn(sensitive, displayed)
        self.assertIn("<REDACTED_GITHUB_TOKEN>", displayed)
        self.assertIn("token=<REDACTED>", displayed)
        self.assertIn("password=<REDACTED>", displayed)
        self.assertIn("<ABS_PATH>", displayed)

    def test_output_bounds_long_message_and_traceback(self):
        frame_lines = [
            f'  File "D:\\a\\StorageScope-Architecte\\module_{i}.py", line {i + 1}, in function_{i}'
            for i in range(20)
        ]
        detail = (
            "Traceback (most recent call last):\n"
            + "\n".join(frame_lines)
            + "\nValueError: "
            + ("x" * 900)
        )
        evidence = build_bounded_diagnostics(detail)
        self.assertEqual(len(evidence["traceback_frames"]), 8)
        self.assertEqual(evidence["traceback_frames"][0]["function"], "function_12")
        self.assertEqual(evidence["traceback_frames"][-1]["function"], "function_19")
        self.assertLessEqual(len(evidence["exception_message"]), 500)
        self.assertEqual(evidence["detail_chars"], len(detail))
        self.assertEqual(len(evidence["detail_sha256"]), 64)
        self.assertFalse(evidence["raw_detail_retained"])

    def test_message_without_traceback_is_still_useful(self):
        evidence = build_bounded_diagnostics("RuntimeError: capacity history is empty")
        self.assertEqual(evidence["exception_type"], "RuntimeError")
        self.assertEqual(evidence["exception_message"], "capacity history is empty")
        self.assertEqual(evidence["traceback_frames"], [])

    def test_markdown_renders_safe_diagnostic_columns(self):
        token = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"
        detail = (
            'Traceback (most recent call last):\n'
            '  File "D:\\a\\StorageScope-Architecte\\StorageScope-Architecte\\'
            'tools\\example.py", line 7, in run\n'
            "RuntimeError: token=private " + token
        )
        report = self._report(detail)
        markdown = render_markdown(report)
        self.assertIn("Exception", markdown)
        self.assertIn("Origine (frames)", markdown)
        self.assertIn("tools/example.py:7::run", markdown)
        self.assertNotIn(token, markdown)
        self.assertNotIn("token=private", markdown)
        self.assertNotIn("D:\\a\\StorageScope-Architecte", markdown)

    def test_diagnostic_projection_never_retains_python_source_excerpt(self):
        detail = (
            '  File "D:\\a\\StorageScope-Architecte\\mod.py", line 8, in run\n'
            "    password = 'SYNTHETIC-PRIVATE-VALUE'\n"
            "RuntimeError: operation rejected"
        )
        evidence = build_bounded_diagnostics(detail)
        serialized = repr(evidence)
        self.assertNotIn("SYNTHETIC-PRIVATE-VALUE", serialized)
        self.assertNotIn("password =", serialized)
        self.assertEqual(evidence["traceback_frames"][0]["file"], "mod.py")


if __name__ == "__main__":
    unittest.main()
