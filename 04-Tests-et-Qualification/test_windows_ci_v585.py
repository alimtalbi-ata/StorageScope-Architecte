import unittest
from pathlib import Path

ROOT=Path(__file__).parent

class WindowsCI585(unittest.TestCase):
    def test_manifest_mapping_is_independent(self):
        ci=(ROOT/'.github/workflows/windows-build.yml').read_text()
        self.assertIn("$item.filename -in @('StorageScope.exe','StorageScope-UpgradeGate.exe')",ci)
        self.assertIn('"dist/$($item.filename)"',ci)
        self.assertIn('"installer/$($item.filename)"',ci)
    def test_manifest_expected_three_artifacts(self):
        ci=(ROOT/'.github/workflows/windows-build.yml').read_text()
        self.assertIn('StorageScope-Setup-v6.17.exe',ci)
        self.assertIn('Compare-Object $expected $actual',ci)
        self.assertIn('Size mismatch',ci)
    def test_upload_paths(self):
        ci=(ROOT/'.github/workflows/windows-build.yml').read_text()
        self.assertIn('            dist/StorageScope.exe\n            dist/StorageScope-UpgradeGate.exe',ci)
    def test_installer_qualification_checks_gate(self):
        script=(ROOT/'qualifier-installation-windows.ps1').read_text()
        self.assertIn("param([string]$Version = '6.17')",script)
        self.assertIn('Upgrade gate absent apres installation',script)
    def test_ci_version(self):
        ci=(ROOT/'.github/workflows/windows-build.yml').read_text()
        self.assertIn('release-manifest-v6.17.json',ci)
        self.assertIn('StorageScope-Windows-v6.17',ci)
