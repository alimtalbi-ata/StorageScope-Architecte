import unittest
from pathlib import Path
ROOT = Path(__file__).parent
class UpgradeInstallerTests(unittest.TestCase):
    def test_inno_blocks_before_file_replacement(self):
        s=(ROOT/'StorageScope.iss').read_text()
        self.assertIn('function PrepareToInstall',s)
        self.assertIn('ExtractTemporaryFile',s)
        self.assertIn('ExitCode <> 0',s)
    def test_gate_is_embedded(self):
        self.assertIn('Flags: dontcopy',(ROOT/'StorageScope.iss').read_text())
    def test_builder_produces_gate_binary(self):
        s=(ROOT/'build-all-windows.ps1').read_text()
        self.assertIn("'StorageScope-UpgradeGate'",s)
        self.assertIn("$gateBinary",s)
    def test_gate_is_fail_closed(self):
        s=(ROOT/'upgrade_gate_v581.py').read_text()
        self.assertIn("return 1",s)
        self.assertIn('verify_backup_snapshot',s)
    def test_version_consistency(self):
        self.assertIn('6.17',(ROOT/'StorageScope.iss').read_text())
        self.assertIn("VERSION = '6.17'",(ROOT/'storagescope_windows.py').read_text())
