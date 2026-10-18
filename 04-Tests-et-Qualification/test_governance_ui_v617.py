"""Structural UI regressions for the responsive governance workspace."""
import ast
from pathlib import Path
import unittest
from windows_accessibility_v617 import display_metrics
BASE=Path(__file__).resolve().parent
class GovernanceUI617Tests(unittest.TestCase):
 def test_grid_search_fields(self):
  source=(BASE/'decision_workspace_ui_v543.py').read_text(encoding='utf8')
  self.assertIn('search_row.columnconfigure(1, weight=3)',source)
  self.assertIn("sticky='ew'",source)
 def test_preset_buttons_two_rows(self):
  source=(BASE/'decision_workspace_ui_v543.py').read_text(encoding='utf8')
  self.assertIn("text='En retard'",source)
  self.assertIn("grid(row=1,column=1",source)
 def test_no_invalid_browse_select_all(self):
  source=(BASE/'decision_workspace_ui_v543.py').read_text(encoding='utf8')
  self.assertNotIn("tree.selection_set(tree.get_children())",source)
 def test_responsive_import_exists(self):
  source=(BASE/'storagescope_windows.py').read_text(encoding='utf8')
  self.assertIn('from windows_accessibility_v617 import display_metrics',source)
 def test_compact_dpi(self):
  self.assertTrue(display_metrics(1920,1080,2)['compact'])
 def test_ui_syntax(self):
  ast.parse((BASE/'decision_workspace_ui_v543.py').read_text(encoding='utf8'))
