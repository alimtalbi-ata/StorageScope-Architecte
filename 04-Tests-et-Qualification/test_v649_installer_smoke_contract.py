import unittest
from pathlib import Path
R = Path(__file__).resolve().parents[1]
class InstallerSmokeContract(unittest.TestCase):
 def test_cleanup_not_claimed_before_uninstall(self):
  t=(R/'02-Compilation-Windows/qualify-installer-smoke-windows.ps1').read_text()
  self.assertIn('$report.installed -and $report.version_checked -and $report.uninstalled -and -not $failure',t)
 def test_cleanup_error_captured(self):
  t=(R/'02-Compilation-Windows/qualify-installer-smoke-windows.ps1').read_text()
  self.assertIn('Cleanup failed:',t)
 def test_report_always_written(self):
  t=(R/'02-Compilation-Windows/qualify-installer-smoke-windows.ps1').read_text()
  self.assertIn('finally {',t)
  self.assertIn('windows-installer-smoke-report.json',t)
 def test_ci_checks_report_status(self):
  t=(R/'.github/workflows/windows-build.yml').read_text()
  self.assertIn("$result.status -ne 'PASS'",t)
 def test_version_consistency(self):
  v=(R/'07-Manifestes/VERSION').read_text(encoding='utf-8').strip(); self.assertRegex(v,r'^\d+\.\d+$'); self.assertGreaterEqual(tuple(map(int,v.split('.'))),(6,49))
  self.assertIn(f'#define AppVersion "{v}"',(R/'02-Compilation-Windows/StorageScope.iss').read_text(encoding='utf-8'))
if __name__=='__main__': unittest.main()
