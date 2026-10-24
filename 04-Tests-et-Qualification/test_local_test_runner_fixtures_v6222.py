"""Regression for historical fixture staging in the local cumulative runner.
Author: Abdelhalim Talbi.
"""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'scripts' / 'run_tests.py'


class LocalRunnerFixtureTests(unittest.TestCase):
    def run_legacy(self, pattern):
        result = subprocess.run([sys.executable, str(RUNNER), '--pattern', pattern],
                                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0,
                         f'{pattern} failed: {result.stdout[-1000:]} {result.stderr[-1500:]}')

    def test_benchmark_helper_is_colocated(self):
        self.run_legacy('test_governance_v659.py')

    def test_capture_disclosure_fixture_is_colocated(self):
        self.run_legacy('test_windows_packaging_v563.py')

    def test_archived_upgrade_workflow_fixture_is_restored(self):
        self.run_legacy('test_windows_portable_v589.py')


if __name__ == '__main__':
    unittest.main()
