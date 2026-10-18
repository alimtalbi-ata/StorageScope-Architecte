"""Build contract tests, not a substitute for native Windows validation."""
import unittest
from pathlib import Path
from unittest.mock import patch
import storagescope_windows as app

ROOT = Path(__file__).parent

class WindowsBuildV568(unittest.TestCase):
    def test_version(self):
        self.assertEqual(app.VERSION, '6.17')
    def test_one_click_entry(self):
        script=(ROOT/'Construire-StorageScope.cmd').read_text()
        self.assertIn('build-all-windows.ps1', script)
        self.assertIn('exit /b 1', script)
    def test_bootstrap_all_tools(self):
        script=(ROOT/'build-all-windows.ps1').read_text()
        for token in ('Python.Python.3.12','JRSoftware.InnoSetup','requirements-build.txt','PyInstaller','--self-test','StorageScope.iss','Get-FileHash'):
            self.assertIn(token, script)
    def test_frozen_imports_explicit(self):
        spec=(ROOT/'StorageScope.spec').read_text()
        self.assertIn('hiddenimports=local_modules',spec)
    def test_installer_includes_frozen_binary(self):
        iss=(ROOT/'StorageScope.iss').read_text()
        self.assertIn('Source: "dist\\StorageScope.exe"',iss)
        self.assertIn('"6.17"',iss)
    def test_ci_publishes_installer(self):
        workflow=(ROOT/'.github/workflows/windows-build.yml').read_text()
        self.assertIn('Construire-StorageScope.cmd',workflow)
        self.assertIn('installer/StorageScope-Setup-v6.17.exe',workflow)
    def test_escape_navigation_present(self):
        self.assertIn("root.bind('<Escape>'",(ROOT/'storagescope_windows.py').read_text())

if __name__ == '__main__': unittest.main()
