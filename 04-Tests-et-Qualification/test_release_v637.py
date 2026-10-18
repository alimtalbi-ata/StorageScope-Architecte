import pathlib, unittest, re
ROOT=pathlib.Path(__file__).resolve().parents[1]
class ReleaseTests(unittest.TestCase):
 def test_version(self):
  self.assertEqual((ROOT/'07-Manifestes/VERSION').read_text().strip(),'6.37')
 def test_entrypoint(self):
  self.assertIn('build-all-windows.ps1',(ROOT/'Construire-StorageScope.cmd').read_text())
 def test_stable_preflight(self):
  self.assertTrue((ROOT/'02-Compilation-Windows/preflight.ps1').exists())
  self.assertIn('preflight.ps1',(ROOT/'02-Compilation-Windows/build-all-windows.ps1').read_text())
 def test_build_artifact_version(self):
  script=(ROOT/'02-Compilation-Windows/build-engine-windows.ps1').read_text()
  self.assertIn('StorageScope-Setup-v6.37.exe',script)
  self.assertIn('release-manifest-v6.37.json',script)
 def test_installer_version(self):
  self.assertIn('#define AppVersion "6.37"',(ROOT/'02-Compilation-Windows/StorageScope.iss').read_text())
 def test_diagnostic_stage(self):
  self.assertIn('diagnostic stage retained',(ROOT/'02-Compilation-Windows/build-all-windows.ps1').read_text())
if __name__=='__main__': unittest.main()
