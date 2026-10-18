import pathlib, unittest, re
ROOT=pathlib.Path(__file__).resolve().parents[1]
class ReleaseContract(unittest.TestCase):
 def test_version(self): self.assertEqual((ROOT/'07-Manifestes/VERSION').read_text().strip(),'6.35')
 def test_scripts(self):
  base=ROOT/'02-Compilation-Windows'
  for name in ('build-all-windows.ps1','build-engine-windows.ps1','StorageScope.iss','preflight-v635.ps1'):
   self.assertTrue((base/name).is_file(),name)
 def test_launcher(self): self.assertIn('build-all-windows.ps1',(ROOT/'Construire-StorageScope.cmd').read_text())
 def test_no_stale_build_version(self):
  base=ROOT/'02-Compilation-Windows'
  for name in ('build-all-windows.ps1','build-engine-windows.ps1','StorageScope.iss'):
   self.assertNotIn('6.34',(base/name).read_text())
if __name__=='__main__': unittest.main()
