"""V6.259 regression tests for diagnostics containing whitespace in paths/secrets.
Synthetic test input only; no historical raw traceback is embedded here.
Author: Abdelhalim Talbi.
"""
import unittest

from tools.classify_windows_regression_log import build_bounded_diagnostics


class HistoricalDiagnosticRedactionV6259(unittest.TestCase):
    def assert_no_leak(self, diagnostic, *fragments):
        evidence = build_bounded_diagnostics(diagnostic)
        message = evidence["exception_message"]
        for fragment in fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, message)
        self.assertFalse(evidence["raw_detail_retained"])
        return evidence

    def test_quoted_windows_path_with_spaces_is_redacted_whole(self):
        evidence = self.assert_no_leak(
            r"FileNotFoundError: missing 'D:\Program Files\StorageScope\private file.json'",
            "Program Files", "StorageScope", "private file.json",
        )
        self.assertEqual(evidence["exception_type"], "FileNotFoundError")
        self.assertIn("missing", evidence["exception_message"])
        self.assertIn("<ABS_PATH>", evidence["exception_message"])

    def test_unquoted_windows_path_with_spaces_does_not_leak_suffix(self):
        evidence = self.assert_no_leak(
            r"RuntimeError: failed at D:\Users\A User\private\evidence file.txt",
            "A User", "private", "evidence file.txt",
        )
        self.assertIn("<ABS_PATH>", evidence["exception_message"])
        self.assertTrue(evidence["exception_message"].startswith("failed at "))

    def test_quoted_posix_path_with_spaces_is_redacted_whole(self):
        evidence = self.assert_no_leak(
            "RuntimeError: missing '/home/runner/work/private user/secret report.json'",
            "private user", "secret report.json", "/home/runner",
        )
        self.assertEqual(evidence["exception_type"], "RuntimeError")
        self.assertIn("missing", evidence["exception_message"])
        self.assertIn("<ABS_PATH>", evidence["exception_message"])

    def test_quoted_multiword_credentials_are_redacted(self):
        diagnostic = (
            'RuntimeError: password="correct horse battery staple" '
            "token='secret with spaces' "
            'api_key="sk-live value with spaces"'
        )
        evidence = self.assert_no_leak(
            diagnostic, "correct horse battery staple", "secret with spaces",
            "sk-live value with spaces",
        )
        message = evidence["exception_message"]
        self.assertIn("password=<REDACTED>", message)
        self.assertIn("token=<REDACTED>", message)
        self.assertIn("api_key=<REDACTED>", message)

    def test_single_token_and_bearer_redaction_remain_compatible(self):
        evidence = self.assert_no_leak(
            "RuntimeError: token=abc123 Bearer sensitive-token",
            "abc123", "sensitive-token",
        )
        self.assertIn("token=<REDACTED>", evidence["exception_message"])
        self.assertIn("Bearer <REDACTED>", evidence["exception_message"])

    def test_unquoted_posix_path_with_spaces_is_fail_closed(self):
        evidence = self.assert_no_leak(
            "RuntimeError: unable to read /home/private user/secret report.csv",
            "private user", "secret report.csv",
        )
        self.assertIn("<ABS_PATH>", evidence["exception_message"])

    def test_unquoted_path_preserves_following_secret_redaction(self):
        evidence = self.assert_no_leak(
            r"RuntimeError: failed at D:\a\StorageScope-Architecte\private\file.py "
            r"token=abc123 password=do-not-store "
            r"ghp_abcdefghijklmnopqrstuvwxyz0123456789",
            "D:\\a", "abc123", "do-not-store",
            "ghp_abcdefghijklmnopqrstuvwxyz0123456789",
        )
        message = evidence["exception_message"]
        self.assertIn("<ABS_PATH>", message)
        self.assertIn("token=<REDACTED>", message)
        self.assertIn("password=<REDACTED>", message)
        self.assertIn("<REDACTED_GITHUB_TOKEN>", message)
