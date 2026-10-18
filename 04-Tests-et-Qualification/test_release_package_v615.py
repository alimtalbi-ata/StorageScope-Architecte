"""Release build layout and version regression tests."""
import unittest
from pathlib import Path
class TestReleaseV615(unittest.TestCase):
 def test_version_file(self):
  self.assertEqual(Path(__file__).with_name("VERSION").read_text().strip(),"6.17")
 def test_windows_script_targets_current_version(self):
  script=Path(__file__).with_name("build-all-windows.ps1").read_text()
  self.assertIn("$expectedVersion = '6.17'",script)
  self.assertIn("-ne '6.17'",script)
 def test_installer_version(self):
  self.assertIn('#define AppVersion "6.17"',Path(__file__).with_name("StorageScope.iss").read_text())
 def test_bootstrap_files_exist(self):
  base=Path(__file__).parent
  for name in ("Construire-StorageScope.cmd","build-all-windows.ps1","StorageScope.spec","StorageScope.iss","requirements-build.txt","verify-windows-build.py"):
   with self.subTest(name=name):self.assertTrue((base/name).is_file())
