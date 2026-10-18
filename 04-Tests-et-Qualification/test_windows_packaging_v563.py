"""Static packaging checks, not a substitute for Windows runtime tests."""
import unittest
from pathlib import Path
from storagescope_windows import VERSION

ROOT = Path(__file__).resolve().parent

class TestWindowsPackaging563(unittest.TestCase):
    def test_version(self):
        self.assertGreaterEqual(tuple(map(int, VERSION.split('.'))), (5, 64))
    def test_installer_files(self):
        for name in ('StorageScope.iss', 'build-installer-windows.ps1', 'build-windows.ps1', 'StorageScope.spec'):
            self.assertTrue((ROOT/name).is_file())
    def test_installer_executable(self):
        spec = (ROOT/'StorageScope.iss').read_text(encoding='utf-8')
        self.assertIn('dist\\StorageScope.exe', spec)
        self.assertIn('PrivilegesRequired=lowest', spec)
    def test_embedded_workspace_api(self):
        import inspect
        from decision_workspace_ui_v543 import open_workspace
        self.assertIn('embedded', inspect.signature(open_workspace).parameters)
    def test_shell_embeds_governance(self):
        src = (ROOT/'storagescope_windows.py').read_text(encoding='utf-8')
        self.assertIn('embedded=True', src)
        self.assertIn("pages['Gouvernance']", src)
    def test_capture_disclosure(self):
        self.assertIn('Aucune capture réelle', (ROOT/'CAPTURES-STATUS-V563.md').read_text(encoding='utf-8'))
