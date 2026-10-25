"""V6.229 — CLI/desktop CMDB evidence parity (synthetic fixtures).
Author: Abdelhalim Talbi.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / '03-Sources' / 'inventory_reconcile_v619.py'


class CmdbCliEvidenceParityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.snapshot = self.root / 'snapshot.json'
        self.report = self.root / 'report.json'

    def run_cli(self, raw, output=True):
        self.snapshot.write_bytes(raw)
        cmd = [sys.executable, str(CLI), str(self.snapshot)]
        if output:
            cmd.extend(['--output', str(self.report)])
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    def test_bom_and_exact_bytes_digest_match_desktop(self):
        raw = b'\xef\xbb\xbf [ {"source":"NetApp", "serial":"S-1"} ]\n'
        result = self.run_cli(raw)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(self.report.read_text(encoding='utf-8'))
        self.assertEqual(report['snapshot_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(report['snapshot_size_bytes'], len(raw))
        self.assertEqual(report['automatic_merges'], 0)

    def test_duplicate_json_keys_are_rejected_without_output(self):
        result = self.run_cli(b'[{"source":"trusted","source":"untrusted","serial":"S1"}]')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.report.exists())

    def test_nan_and_infinity_rejected_without_output(self):
        for value in (b'NaN', b'Infinity', b'-Infinity'):
            with self.subTest(value=value):
                result = self.run_cli(b'[{"source":"a","serial":"S1","size":' + value + b'}]')
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.report.exists())

    def test_oversized_snapshot_rejected_without_output(self):
        raw = b'[{"source":"a","serial":"S1","description":"' + b'x' * (8 * 1024 * 1024) + b'"}]'
        result = self.run_cli(raw)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.report.exists())

    def test_existing_report_not_overwritten(self):
        self.report.write_text('existing evidence', encoding='utf-8')
        result = self.run_cli(b'[{"source":"a","serial":"S1"}]')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.report.read_text(encoding='utf-8'), 'existing evidence')

    def test_invalid_snapshot_never_prints_json(self):
        result = self.run_cli(b'[{"source":"a","source":"b","serial":"S1"}]', output=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
