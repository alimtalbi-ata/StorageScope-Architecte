import unittest, tempfile, shutil
from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('verify',Path(__file__).resolve().parents[1]/'02-Compilation-Windows'/'verify-windows-build.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
ROOT = Path(__file__).parent
module.ROOT = ROOT
validate=module.validate
class BuildV578(unittest.TestCase):
    def test_preflight(self): self.assertEqual(validate(), (ROOT/'VERSION').read_text(encoding='utf-8').strip())
    def test_delegation(self):
        for name in ('build-windows.ps1','build-installer-windows.ps1'):
            self.assertIn('build-all-windows.ps1', (ROOT/name).read_text())
    def test_ci_installer(self):
        ci=(ROOT/'.github/workflows/windows-build.yml').read_text()
        self.assertIn('StorageScope-Setup-v6.17.exe',ci)
    def test_build_preflight(self):
        self.assertIn('verify-windows-build.py',(ROOT/'build-all-windows.ps1').read_text())
    def test_install_data_protection(self):
        self.assertNotIn('Remove-Item',(ROOT/'qualifier-installation-windows.ps1').read_text())
