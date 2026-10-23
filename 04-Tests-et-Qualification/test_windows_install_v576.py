import unittest
from pathlib import Path
R=Path(__file__).parent
class WindowsInstallQualificationV578(unittest.TestCase):
    def test_script_present(self):
        self.assertTrue((R/'qualifier-installation-windows.ps1').exists())
    def test_silent_install_and_uninstall(self):
        s=(R/'qualifier-installation-windows.ps1').read_text()
        for x in ('/VERYSILENT','unins000.exe','--self-test','PRESERVE-V578'):
            self.assertIn(x,s)
    def test_fail_closed_on_existing_user_data(self):
        s=(R/'qualifier-installation-windows.ps1').read_text()
        self.assertIn('donnees utilisateur preexistantes',s)
        self.assertNotIn('Remove-Item',s)
    def test_ci_runs_qualification(self):
        s=(R/'.github/workflows/windows-build.yml').read_text()
        self.assertIn('Qualify installer rejection',s)
        self.assertIn('Install and uninstall smoke test',s)
        self.assertIn('qualify-installer-smoke-windows.ps1',s)
        self.assertIn('windows-installer-smoke-report.json',s)
    def test_installer_is_per_user(self):
        s=(R/'StorageScope.iss').read_text()
        self.assertIn('PrivilegesRequired=lowest',s)
        self.assertIn('DefaultDirName={localappdata}',s)
