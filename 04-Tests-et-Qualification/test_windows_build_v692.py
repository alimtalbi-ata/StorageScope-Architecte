import unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class TestBuildExitCodes(unittest.TestCase):
 def test_build_engine_native_exit_code(self):
  s=(R/'02-Compilation-Windows/build-all-windows.ps1').read_text();self.assertIn('Build engine returned exit code',s)
 def test_preflight_native_exit_code(self):
  s=(R/'02-Compilation-Windows/build-all-windows.ps1').read_text();self.assertIn('Preflight returned exit code',s)
 def test_ci_build_exit_code(self):
  s=(R/'.github/workflows/windows-build.yml').read_text();self.assertIn('Build process returned',s)
 def test_ci_smoke_exit_code(self):
  s=(R/'.github/workflows/windows-build.yml').read_text();self.assertIn('Installer smoke test returned',s)
 def test_no_fake_binaries(self):
  self.assertFalse(list((R/'binary').rglob('*.exe')))
if __name__=='__main__': unittest.main()
