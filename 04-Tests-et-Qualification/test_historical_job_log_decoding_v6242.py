"""Regression tests for fail-closed CI job-log byte decoding.

Author: Abdelhalim Talbi.
"""
import hashlib
import io
import unittest
import zipfile

from tools.strict_job_log_payload import decode_github_actions_job_log_payload


class StrictJobLogPayloadV6242(unittest.TestCase):
    def test_raw_utf8_preserves_ansi_and_reports_exact_payload_hash(self):
        payload = "échec\n\x1b[31mERROR: exemple\x1b[0m\n".encode("utf-8")
        text, evidence = decode_github_actions_job_log_payload(payload)
        self.assertEqual(text.encode("utf-8"), payload)
        self.assertEqual(evidence["payload_sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(evidence["payload_byte_count"], len(payload))
        self.assertFalse(evidence["lossy_decoding_used"])
        self.assertEqual(evidence["transport"], "raw")

    def test_utf8_bom_is_handled_without_replacing_bytes(self):
        payload = b"\xef\xbb\xbfRan 1 test in 0.01s\nFAILED (errors=1)\n"
        text, evidence = decode_github_actions_job_log_payload(payload)
        self.assertTrue(text.startswith("Ran 1 test"))
        self.assertTrue(evidence["utf8_bom_stripped"])
        self.assertEqual(evidence["payload_sha256"], hashlib.sha256(payload).hexdigest())

    def test_invalid_raw_utf8_fails_closed_with_offset_and_hash(self):
        payload = b"Ran 1 test\nERROR: bad-\xffbyte\n"
        with self.assertRaisesRegex(ValueError, r"not valid UTF-8.*byte_offset=.*payload_sha256="):
            decode_github_actions_job_log_payload(payload)

    def test_single_text_member_in_zip_is_decoded_and_bound_to_archive_hash(self):
        output = io.BytesIO()
        payload = "Ran 1 test in 0.01s\nFAILED (errors=1)\n".encode("utf-8")
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("job.log", payload)
        downloaded = output.getvalue()
        text, evidence = decode_github_actions_job_log_payload(downloaded)
        self.assertEqual(text, payload.decode("utf-8"))
        self.assertEqual(evidence["transport"], "zip_member")
        self.assertEqual(evidence["zip_member"], "job.log")
        self.assertEqual(evidence["download_sha256"], hashlib.sha256(downloaded).hexdigest())
        self.assertEqual(evidence["payload_sha256"], hashlib.sha256(payload).hexdigest())

    def test_invalid_utf8_inside_zip_fails_closed(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as zf:
            zf.writestr("job.log", b"ERROR: invalid \xff\n")
        with self.assertRaisesRegex(ValueError, "not valid UTF-8"):
            decode_github_actions_job_log_payload(output.getvalue())

    def test_archive_with_multiple_candidate_logs_is_rejected(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as zf:
            zf.writestr("one.log", "first")
            zf.writestr("two.txt", "second")
        with self.assertRaisesRegex(ValueError, "exactly one text log member"):
            decode_github_actions_job_log_payload(output.getvalue())

    def test_nul_bytes_are_rejected_as_probable_binary_input(self):
        with self.assertRaisesRegex(ValueError, "contains NUL"):
            decode_github_actions_job_log_payload(b"text\x00more text")

    def test_empty_and_non_byte_inputs_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            decode_github_actions_job_log_payload(b"")
        with self.assertRaisesRegex(TypeError, "must be bytes"):
            decode_github_actions_job_log_payload("not bytes")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
