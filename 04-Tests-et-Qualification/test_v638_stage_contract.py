import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BUILD=(ROOT/'02-Compilation-Windows/build-all-windows.ps1').read_text(encoding='utf-8')
VERIFY=(ROOT/'02-Compilation-Windows/verify-windows-build.py').read_text(encoding='utf-8')
class TestStage(unittest.TestCase):
 def test_required_stage_files(self):
  for name in ('Construire-StorageScope.cmd','qualifier-installation-windows.ps1','qualifier-executable-windows.ps1','windows-build.yml'):
   self.assertIn(name,BUILD)
 def test_version(self):
  self.assertEqual((ROOT/'07-Manifestes/VERSION').read_text().strip(),'6.38')
 def test_version_build(self):
  self.assertIn("$expectedVersion = '6.38'",(ROOT/'02-Compilation-Windows/build-engine-windows.ps1').read_text())
 def test_version_preflight(self):
  self.assertIn("$version -ne '6.38'",(ROOT/'02-Compilation-Windows/preflight.ps1').read_text())
 def test_verifier_contract(self):
  self.assertIn('qualifier-installation-windows.ps1',VERIFY)
if __name__=='__main__': unittest.main()
