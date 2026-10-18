import unittest
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text=(ROOT/'.github/workflows/windows-build.yml').read_text(encoding='utf-8')
    def test_powershell_version_regex_has_single_backslash(self):
        self.assertIn(r"'^\d+\.\d+$'",self.text)
        self.assertNotIn(r"'^\\d+\\.\\d+$'",self.text)
    def test_qualified_upload_is_gated(self):
        self.assertRegex(self.text,r"(?s)Gate release artifacts.*?if: success\(\).*?StorageScope-Windows-QUALIFIED")
    def test_qualification_reports_checked(self):
        for n in ('windows-qualification-report.json','windows-installer-smoke-report.json','windows-portable-smoke-report.json'):
            self.assertIn(n,self.text)
        self.assertIn('Empty qualification evidence',self.text)
    def test_diagnostics_always_uploaded(self):
        self.assertRegex(self.text,r"(?s)if: always\(\).*?StorageScope-Windows-DIAGNOSTICS")
if __name__=='__main__':unittest.main()
