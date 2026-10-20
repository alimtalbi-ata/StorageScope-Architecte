"""Architecture contract regression: version alignment and isolated pagination (stdlib)."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class ArchitectureContracts(unittest.TestCase):
    def test_version_manifest_exists(self):
        value = (ROOT / '07-Manifestes' / 'VERSION').read_text(encoding='utf-8').strip()
        self.assertRegex(value, r'^\d+\.\d+$')

    def test_windows_build_contracts_present(self):
        for name in ('build-all-windows.ps1','StorageScope.iss','verify-binary-delivery.py'):
            with self.subTest(name=name):
                self.assertTrue((ROOT / '02-Compilation-Windows' / name).is_file())

    def test_installer_keeps_upgrade_gate(self):
        script = (ROOT / '02-Compilation-Windows' / 'StorageScope.iss').read_text(encoding='utf-8')
        self.assertIn('PrepareToInstall', script)
        self.assertIn('StorageScope-UpgradeGate.exe', script)

    def test_target_architecture_documented(self):
        self.assertTrue((ROOT / '05-Documentation' / 'ARCHITECTURE-CIBLE-ET-ROADMAP-v6114.md').is_file())

if __name__ == '__main__':
    unittest.main()
