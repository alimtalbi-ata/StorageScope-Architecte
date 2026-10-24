"""Regression checks for resizeable business panels. Author: Abdelhalim Talbi."""
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
class LayoutV571Tests(unittest.TestCase):
    def test_governance_paned(self):
        code=(ROOT/'decision_workspace_ui_v543.py').read_text()
        self.assertIn("ttk.Panedwindow(window, orient='vertical')",code)
        self.assertIn('split.add(detail_frame, weight=2)',code)
    def test_governance_scrollbars(self):
        code=(ROOT/'decision_workspace_ui_v543.py').read_text()
        self.assertIn("hscroll.grid(row=1, column=0, sticky='ew')",code)
        self.assertIn("scrollbar.grid(row=0, column=1, sticky='ns')",code)
    def test_campaign_scrollbars(self):
        code=(ROOT/'campaign_dashboard_v527.py').read_text()
        self.assertIn("hscroll.grid(row=1, column=0, sticky='ew')",code)
        self.assertIn("vscroll.grid(row=0, column=1, sticky='ns')",code)
    def test_version(self):
        from storagescope_windows import VERSION
        release=(ROOT/'VERSION').read_text(encoding='utf-8').strip()
        self.assertEqual(VERSION,release)
        self.assertGreaterEqual(tuple(map(int,release.split('.'))),(6,17))
if __name__=='__main__': unittest.main()
