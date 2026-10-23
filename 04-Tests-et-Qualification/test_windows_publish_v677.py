"""Static regression guards for Windows publication staging."""
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / '02-Compilation-Windows' / 'build-all-windows.ps1'

class PublishContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = SCRIPT.read_text(encoding='utf-8')

    def test_publish_staging_precedes_replacement(self):
        self.assertLess(self.script.index("$publishRoot ="), self.script.index('--pending $publishRoot'))

    def test_hashes_checked_before_replacement(self):
        self.assertLess(self.script.index('Publication alteree:'), self.script.index('--pending $publishRoot'))

    def test_all_release_outputs_required(self):
        for filename in ('StorageScope.exe','StorageScope-UpgradeGate.exe','StorageScope-Setup-v$releaseVersion.exe','release-manifest-v$releaseVersion.json','StorageScope-Portable-v$releaseVersion-win-x64.zip'):
            self.assertIn(filename, self.script)

    def test_failed_stage_retained(self):
        self.assertIn('diagnostic stage retained', self.script)

if __name__ == '__main__': unittest.main()
