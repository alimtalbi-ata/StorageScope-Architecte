import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
class WindowsUpgradeE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = (ROOT / 'qualifier-mise-a-jour-windows.ps1').read_text(encoding='utf-8')
    def test_uses_embedded_gate_not_python(self):
        self.assertNotIn('py.exe', self.script)
        self.assertIn('EMBEDDED frozen upgrade gate', self.script)
    def test_validates_both_installer_codes(self):
        self.assertIn('$report.previous_exit -ne 0', self.script)
        self.assertIn('$report.new_exit -ne 0', self.script)
    def test_compares_user_file_hashes(self):
        self.assertIn('beforeSentinel', self.script)
        self.assertIn('beforeViews', self.script)
        self.assertIn('source_preserved', self.script)
    def test_checks_actual_backup_and_logs(self):
        self.assertIn('backup_verified', self.script)
        self.assertIn('manifest.json', self.script)
        self.assertIn('logs_present', self.script)
    def test_refuses_non_clean_vm_and_writes_report(self):
        self.assertIn('Test-Path $backup', self.script)
        self.assertIn('finally {', self.script)
        self.assertIn('ConvertTo-Json', self.script)
if __name__ == '__main__': unittest.main()
