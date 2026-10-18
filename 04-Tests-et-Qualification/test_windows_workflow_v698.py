import unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class PowerShellExitTests(unittest.TestCase):
 def test_workflow_script_calls_use_success_flag(self):
  w=(R/'.github/workflows/windows-build.yml').read_text()
  for name in ('Build failed','Native qualification failed','Installer smoke test failed','Portable smoke test failed'):
   self.assertIn(name,w)
 def test_workflow_no_stale_exitcode_checks(self):
  w=(R/'.github/workflows/windows-build.yml').read_text()
  for name in ('Build process returned','Native qualification returned','Installer smoke test returned','Portable smoke returned'):
   self.assertNotIn(name,w)
 def test_build_no_stale_exitcode_after_powershell(self):
  b=(R/'02-Compilation-Windows/build-all-windows.ps1').read_text()
  self.assertNotIn('Preflight returned exit code',b)
  self.assertNotIn('Build engine returned exit code',b)
 def test_python_exitcode_checks_retained(self):
  b=(R/'02-Compilation-Windows/build-all-windows.ps1').read_text()
  self.assertIn('Transactional publication failed',b)
  self.assertIn('Validation binary echouee',b)
if __name__=='__main__': unittest.main()
