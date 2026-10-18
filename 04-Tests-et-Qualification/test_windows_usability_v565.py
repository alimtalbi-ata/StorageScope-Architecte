"""Static integration checks for the Windows desktop shell. Author: Abdelhalim Talbi."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class WindowsUsabilityTests(unittest.TestCase):
    def test_search_shortcut(self):
        self.assertIn("'<Control-f>'",(ROOT/'storagescope_windows.py').read_text())
    def test_search_has_no_automatic_side_effects(self):
        s=(ROOT/'storagescope_windows.py').read_text()
        self.assertIn("search_entry.bind('<Return>'",s)
        self.assertIn("search_destination()",s)
    def test_governance_horizontal_scroll(self):
        self.assertIn('xscrollcommand=hscroll.set',(ROOT/'decision_workspace_ui_v543.py').read_text())
    def test_campaign_scrollbars(self):
        s=(ROOT/'campaign_dashboard_v527.py').read_text()
        self.assertIn('yscrollcommand=vscroll.set',s)
        self.assertIn('xscrollcommand=hscroll.set',s)
    def test_version(self):
        self.assertIn("VERSION = '6.17'",(ROOT/'storagescope_windows.py').read_text())
if __name__=='__main__': unittest.main()
