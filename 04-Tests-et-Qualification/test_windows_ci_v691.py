import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class CIContract(unittest.TestCase):
 def test_ci_verifies_binary(self):
  s=(ROOT/'.github/workflows/windows-build.yml').read_text()
  self.assertIn('Validate published binary deliverables',s)
  self.assertIn('verify-binary-delivery.py',s)
 def test_ci_uploads_binary(self):
  self.assertIn('binary/v*/**',(ROOT/'.github/workflows/windows-build.yml').read_text())
 def test_no_stale_version_in_cmd(self):
  for p in [ROOT/'Construire-StorageScope.cmd',ROOT/'02-Compilation-Windows/Construire-StorageScope.cmd']:
   self.assertNotIn('v6.89',p.read_text())
 def test_binary_not_fabricated(self):
  self.assertFalse(list((ROOT/'binary').rglob('*.exe')))
 def test_version(self):
  self.assertEqual((ROOT/'07-Manifestes/VERSION').read_text().strip(),'6.91')
if __name__=='__main__': unittest.main()
