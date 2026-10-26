"""Regression tests for strict UTF-8 subprocess capture in the Windows suite runner.

The runner must store the exact child bytes before decoding and must never turn
invalid bytes into a success-shaped test log. Author: Abdelhalim Talbi.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.strict_subprocess_output import decode_subprocess_output
from scripts import run_historical_windows_suite as runner


class StrictSubprocessOutputV6243(unittest.TestCase):
    def test_valid_utf8_is_preserved_and_hash_bound(self):
        raw = "Test réussi — échec volontaire imbriqué\n".encode("utf-8")
        text, meta = decode_subprocess_output(raw)
        self.assertEqual(text.encode("utf-8"), raw)
        self.assertEqual(meta["payload_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(meta["payload_byte_count"], len(raw))
        self.assertIs(meta["lossy_decoding_used"], False)

    def test_invalid_utf8_is_rejected_with_byte_offset_and_digest(self):
        raw = b"Ran 1 test\nERROR: invalid-\xffbyte\n"
        with self.assertRaisesRegex(
            ValueError,
            r"not valid UTF-8.*byte_offset=\d+.*payload_sha256=[0-9a-f]{64}",
        ):
            decode_subprocess_output(raw)

    def test_cp1252_only_output_is_not_guessed_or_repaired(self):
        with self.assertRaisesRegex(ValueError, "not valid UTF-8"):
            decode_subprocess_output(b"caf\xe9")

    def test_nul_bearing_output_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError, r"contains NUL.*payload_sha256=[0-9a-f]{64}"
        ):
            decode_subprocess_output(b"OK\x00FAILED")

    def test_empty_bytes_are_decoded_but_left_for_summary_gate_to_reject(self):
        text, meta = decode_subprocess_output(b"")
        self.assertEqual(text, "")
        self.assertEqual(meta["payload_byte_count"], 0)

    @staticmethod
    def _make_root(root: Path) -> None:
        helper = root / "scripts" / "unittest_discover_with_result.py"
        helper.parent.mkdir(parents=True)
        helper.write_text(
            "# test fixture; subprocess.run is replaced by this test\n",
            encoding="utf-8",
        )

    def test_run_suite_fails_closed_and_preserves_invalid_raw_bytes(self):
        raw = b"Ran 1 test\nERROR: invalid-\xffbyte\n"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._make_root(root)
            evidence = root / "evidence"
            completed = subprocess.CompletedProcess(["python"], 1, stdout=raw)
            with patch.object(runner.subprocess, "run", return_value=completed):
                result = runner.run_suite(
                    root / "tests", "test_*.py", root, {}, 1,
                    "invalid-encoding", evidence,
                )
            log = evidence / "historical-suite-invalid-encoding.log"
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(
                result["subprocess_output_decoding"]["status"], "REJECTED"
            )
            self.assertEqual(log.read_bytes(), raw)
            self.assertEqual(result["log_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertIs(
                result["subprocess_output_decoding"]["lossy_decoding_used"], False
            )

    def test_run_suite_accepts_only_authoritative_utf8_marker(self):
        def fake_run(command, **kwargs):
            token = command[command.index("--result-token") + 1]
            payload = {
                "status": "OK",
                "tests_run": 1,
                "failures": 0,
                "errors": 0,
                "skipped": 0,
                "expected_failures": 0,
                "unexpected_successes": 0,
            }
            output = (
                runner.RUNNER_RESULT_PREFIX + token + ": "
                + json.dumps(payload, separators=(",", ":")) + "\n"
            ).encode("utf-8")
            return subprocess.CompletedProcess(command, 0, stdout=output)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._make_root(root)
            evidence = root / "evidence"
            with patch.object(runner.subprocess, "run", side_effect=fake_run):
                result = runner.run_suite(
                    root / "tests", "test_*.py", root, {}, 1,
                    "valid-utf8", evidence,
                )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(
                result["subprocess_output_decoding"]["status"], "ACCEPTED"
            )
            self.assertIs(
                result["subprocess_output_decoding"]["lossy_decoding_used"], False
            )


if __name__ == "__main__":
    unittest.main()
