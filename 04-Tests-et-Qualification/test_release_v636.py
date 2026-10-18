import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class ReleaseContracts(unittest.TestCase):
 def test_version(self): self.assertEqual((ROOT/'07-Manifestes/VERSION').read_text().strip(),'6.36')
 def test_stage_inputs(self):
  s=(ROOT/'02-Compilation-Windows/build-all-windows.ps1').read_text()
  for n in ('StorageScope.spec','StorageScope.iss','requirements-build.txt','verify-windows-build.py'): self.assertIn(n,s)
 def test_preflight(self): self.assertTrue((ROOT/'02-Compilation-Windows/preflight-v636.ps1').exists())
 def test_installer_version(self): self.assertIn('6.36',(ROOT/'02-Compilation-Windows/StorageScope.iss').read_text())
if __name__=='__main__': unittest.main()
