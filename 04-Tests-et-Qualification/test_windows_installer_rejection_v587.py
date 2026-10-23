import unittest
from pathlib import Path
ROOT=Path(__file__).parent
class InstallerRejection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ps=(ROOT/'qualifier-echec-installateur-windows.ps1').read_text()
        cls.ci=(ROOT/'.github/workflows/windows-build.yml').read_text()
    def test_refuse_preexisting_data(self): self.assertIn('VM non vierge',self.ps)
    def test_corrupt_fixture(self): self.assertIn('NOT-A-SQLITE-DATABASE',self.ps)
    def test_fail_closed_checks(self):
        for x in ('exit_code','source_unchanged','installed_binary_present','log_bytes','passed='):
            self.assertIn(x,self.ps)
    def test_cleanup_exact_fixture_only(self): self.assertIn('Fixture modified: left in place',self.ps)
    def test_ci_order(self):
        self.assertLess(self.ci.index('Qualify installer rejection'),self.ci.index('Install and uninstall smoke test'))
        self.assertIn('installer-rejected-v{0}.json',self.ci)
        self.assertIn('RUNNER_ENVIRONMENT',self.ci)
        self.assertIn('source_unchanged',self.ci)
        self.assertIn('installed_binary_present',self.ci)
