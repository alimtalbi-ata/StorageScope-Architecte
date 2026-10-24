"""Current Windows build contracts; historical version V5.68 is a minimum, not a pin.

These checks run inside the isolated historical checkout. Native Windows
installation, binary signatures and runtime qualification remain CI gates.
Author: Abdelhalim Talbi.
"""
import re
import unittest
from pathlib import Path

import storagescope_windows as app

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent


class WindowsBuildV568(unittest.TestCase):
    def test_version(self):
        release = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(release, r"^\d+\.\d+$")
        self.assertEqual(app.VERSION, release)
        major, minor = map(int, release.split("."))
        self.assertGreaterEqual((major, minor), (6, 17))
        iss = (ROOT / "StorageScope.iss").read_text(encoding="utf-8")
        self.assertIn(f'#define AppVersion "{release}"', iss)

    def test_one_click_entry(self):
        wrapper = (ROOT / "Construire-StorageScope.cmd").read_text(encoding="utf-8")
        entry = (REPO / "Construire-StorageScope.cmd").read_text(encoding="utf-8")
        self.assertIn("..\\Construire-StorageScope.cmd", wrapper)
        self.assertIn("exit /b %ERRORLEVEL%", wrapper)
        self.assertIn("build-all-windows.ps1", entry)
        self.assertIn("if errorlevel 1", entry.lower())
        self.assertIn("exit /b 1", entry)

    def test_bootstrap_all_tools(self):
        outer = (ROOT / "build-all-windows.ps1").read_text(encoding="utf-8")
        engine = (ROOT / "build-engine-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("build-engine-windows.ps1", outer)
        self.assertIn("$unfinishedJournal", outer)
        for token in ("Python.Python.3.12", "JRSoftware.InnoSetup",
                      "requirements-build.txt", "PyInstaller", "--self-test",
                      "StorageScope.iss", "Get-FileHash"):
            with self.subTest(token=token):
                self.assertIn(token, engine)

    def test_frozen_imports_explicit(self):
        spec = (ROOT / "StorageScope.spec").read_text(encoding="utf-8")
        self.assertIn("hiddenimports=local_modules", spec)
        self.assertIn("storagescope_windows.py", spec)

    def test_installer_includes_frozen_binary(self):
        iss = (ROOT / "StorageScope.iss").read_text(encoding="utf-8")
        self.assertIn('Source: "dist\\StorageScope.exe"; DestDir: "{app}"', iss)
        # The gate must be both extracted for pre-upgrade checks AND installed.
        self.assertIn('Source: "dist\\StorageScope-UpgradeGate.exe"; Flags: dontcopy', iss)
        self.assertIn('Source: "dist\\StorageScope-UpgradeGate.exe"; DestDir: "{app}"', iss)
        self.assertIn("PrepareToInstall", iss)

    def test_ci_publishes_installer(self):
        workflow = (ROOT / ".github/workflows/windows-build.yml").read_text(encoding="utf-8")
        self.assertIn("02-Compilation-Windows/build-all-windows.ps1", workflow)
        self.assertIn("Gate release artifacts on complete qualification", workflow)
        self.assertIn("StorageScope-Windows-QUALIFIED", workflow)
        self.assertIn("binary/v*/**", workflow)
        self.assertIn("if: success()", workflow)

    def test_escape_navigation_present(self):
        source = (ROOT / "storagescope_windows.py").read_text(encoding="utf-8")
        self.assertIn("root.bind('<Escape>'", source)


if __name__ == "__main__":
    unittest.main()
