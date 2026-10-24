import unittest
from pathlib import Path
ROOT=Path(__file__).parent
class WindowsWorkflow574(unittest.TestCase):
    def test_reset_filters(self):
        text=(ROOT/'decision_workspace_ui_v543.py').read_text()
        self.assertIn('def reset_filters():',text)
        self.assertIn("status.set('all'); deadline.set('all')",text)
    def test_selection_restored_by_decision_id(self):
        text=(ROOT/'decision_workspace_ui_v543.py').read_text()
        self.assertIn('selected_decision =',text)
        self.assertIn('tree.selection_set(node)',text)
    def test_stale_build_removed(self):
        text=(ROOT/'build-all-windows.ps1').read_text()
        self.assertIn("if (Test-Path -LiteralPath $stage)",text)
        self.assertIn('Ancien repertoire de compilation a examiner',text)
        self.assertIn('07-Manifestes/VERSION',text)
    def test_single_installer_check(self):
        text=(ROOT/'build-all-windows.ps1').read_text()
        self.assertIn('Missing build output: $requiredOutput',text)
        self.assertIn('installer/StorageScope-Setup-v$releaseVersion.exe',text)
        self.assertIn('verify-binary-delivery.py',text)
