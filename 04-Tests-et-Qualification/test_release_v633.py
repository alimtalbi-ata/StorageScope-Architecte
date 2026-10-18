from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class ReleaseTests(unittest.TestCase):
 def test_release_version(self):
  self.assertEqual((ROOT/'07-Manifestes/VERSION').read_text().strip(),'6.33')
 def test_entrypoint_direct(self):
  s=(ROOT/'Construire-StorageScope.cmd').read_text()
  self.assertIn('build-all-windows.ps1',s)
  self.assertNotIn('xcopy',s.lower())
 def test_stage_contains_tests(self):
  self.assertIn('04-Tests-et-Qualification/test_*.py',(ROOT/'02-Compilation-Windows/build-all-windows.ps1').read_text())
 def test_versions(self):
  self.assertIn("VERSION = '6.33'",(ROOT/'03-Sources/storagescope_windows.py').read_text())
  self.assertIn('#define AppVersion "6.33"',(ROOT/'02-Compilation-Windows/StorageScope.iss').read_text())
if __name__=='__main__': unittest.main()
