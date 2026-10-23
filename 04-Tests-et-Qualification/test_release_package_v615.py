"""v6.15 release build layout and current-version consistency regressions.

A historical test must preserve its original safety contract without demanding
that the live release still carry the historical v6.17 version string.
Author: Abdelhalim Talbi.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "02-Compilation-Windows"
MANIFEST = ROOT / "07-Manifestes/VERSION"


class TestReleaseV615(unittest.TestCase):
    def current_version(self):
        version = MANIFEST.read_text(encoding="utf-8").strip()
        self.assertRegex(version, r"^\d+\.\d+$")
        self.assertGreaterEqual(tuple(map(int, version.split("."))), (6, 17))
        return version

    def test_version_file(self):
        current = self.current_version()
        staged = ROOT / "04-Tests-et-Qualification/VERSION"
        if staged.exists():
            self.assertEqual(staged.read_text(encoding="utf-8").strip(), current,
                             "Staged historical VERSION must match canonical manifest")

    def test_windows_script_targets_current_version(self):
        script = (BUILD / "build-all-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("$releaseVersion = (Get-Content", script)
        self.assertIn("07-Manifestes/VERSION", script)
        self.assertIn("StorageScope-Setup-v$releaseVersion.exe", script)
        engine = (BUILD / "build-engine-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("$expectedVersion = $releaseVersion", engine)
        self.assertNotIn("$expectedVersion = '6.17'", script)

    def test_installer_version(self):
        version = self.current_version()
        self.assertIn(f'#define AppVersion "{version}"',
                      (BUILD / "StorageScope.iss").read_text(encoding="utf-8"))

    def test_bootstrap_files_exist(self):
        for name in ("Construire-StorageScope.cmd", "build-all-windows.ps1",
                     "StorageScope.spec", "StorageScope.iss",
                     "requirements-build.txt", "verify-windows-build.py"):
            with self.subTest(name=name):
                self.assertTrue((BUILD / name).is_file())


if __name__ == "__main__":
    unittest.main()
