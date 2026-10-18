import unittest
from pathlib import Path
ROOT = Path(__file__).parent
class ReleaseV575(unittest.TestCase):
    def test_transcript(self):
        s=(ROOT/'build-all-windows.ps1').read_text()
        self.assertIn('Start-Transcript',s)
        self.assertIn('Stop-Transcript',s)
    def test_manifest(self):
        s=(ROOT/'build-all-windows.ps1').read_text()
        self.assertIn('release-manifest-v6.17.json',s)
        self.assertIn('sha256',s)
        self.assertIn('generated_utc',s)
    def test_fail_closed(self):
        s=(ROOT/'build-all-windows.ps1').read_text()
        self.assertIn('throw "Artefact vide',s)
        self.assertIn('finally {',s)
    def test_per_user_install(self):
        s=(ROOT/'StorageScope.iss').read_text()
        self.assertIn('PrivilegesRequired=lowest',s)
        self.assertIn('DefaultDirName={localappdata}\\Programs\\StorageScope',s)
    def test_ci_evidence(self):
        s=(ROOT/'.github/workflows/windows-build.yml').read_text()
        self.assertIn('build-logs/*.log',s)
        self.assertIn('installer/release-manifest-v6.17.json',s)
