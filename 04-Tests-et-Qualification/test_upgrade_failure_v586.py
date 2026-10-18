import tempfile
import unittest
from pathlib import Path
from upgrade_failure_qualification_v586 import qualify, main
from unittest.mock import patch

class NegativePathQualificationTests(unittest.TestCase):
    def test_all_cases_pass(self):
        self.assertTrue(qualify()['passed'])
    def test_corrupt_database_blocks(self):
        case = next(c for c in qualify()['cases'] if c['case'] == 'corrupt_sqlite')
        self.assertTrue(case['blocked'])
        self.assertTrue(case['source_unchanged'])
    def test_unsafe_backup_blocks(self):
        self.assertTrue(next(c for c in qualify()['cases'] if c['case'] == 'unsafe_backup_location')['blocked'])
    def test_valid_database_creates_backup(self):
        self.assertFalse(next(c for c in qualify()['cases'] if c['case'] == 'valid_data')['blocked'])
    def test_machine_readable_report(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'report.json'
            with patch('sys.argv', ['qualifier', '--report', str(target)]):
                self.assertEqual(main(), 0)
            self.assertTrue(target.is_file())
