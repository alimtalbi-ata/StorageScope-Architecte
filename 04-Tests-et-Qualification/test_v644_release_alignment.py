import unittest, pathlib, re
ROOT=pathlib.Path(__file__).resolve().parents[1]
class ReleaseAlignment(unittest.TestCase):
 def test_source_version(self):
  version=(ROOT/'07-Manifestes/VERSION').read_text().strip()
  self.assertIn("VERSION = '%s'"%version,(ROOT/'03-Sources/storagescope_windows.py').read_text())
 def test_inno_version(self):
  version=(ROOT/'07-Manifestes/VERSION').read_text().strip()
  self.assertIn('#define AppVersion "%s"'%version,(ROOT/'02-Compilation-Windows/StorageScope.iss').read_text())
 def test_stage_has_verifier_dependencies(self):
  text=(ROOT/'02-Compilation-Windows/build-all-windows.ps1').read_text()
  self.assertIn("'build-all-windows.ps1','build-engine-windows.ps1'",text)
 def test_ci_not_stale(self):
  text=(ROOT/'03-Sources/.github/workflows/windows-build.yml').read_text()
  self.assertNotIn('v6.11',text)
  self.assertIn('02-Compilation-Windows/build-all-windows.ps1',text)
 def test_build_logs_persist(self):
  text=(ROOT/'02-Compilation-Windows/build-all-windows.ps1').read_text()
  self.assertIn("'portable','build-logs'",text)
if __name__=='__main__': unittest.main()
