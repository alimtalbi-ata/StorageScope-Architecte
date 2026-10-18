"""Static integration and compatibility checks. Author: Abdelhalim Talbi."""
import ast
import unittest
from pathlib import Path
from decision_workspace_ui_v543 import open_workspace
from decision_workspace_v542 import workspace
from decision_views_v543 import SavedViews

ROOT=Path(__file__).parent
class UnifiedGovernanceTests(unittest.TestCase):
    def test_dashboard_compiles(self): ast.parse((ROOT/'campaign_dashboard_v527.py').read_text())
    def test_workspace_ui_compiles(self): ast.parse((ROOT/'decision_workspace_ui_v543.py').read_text())
    def test_one_governance_entry(self):
        s=(ROOT/'campaign_dashboard_v527.py').read_text()
        self.assertEqual(s.count("text='Gouvernance', command=show_governance_workspace"),1)
    def test_legacy_button_removed(self): self.assertNotIn("text='Suivi décisions'",(ROOT/'campaign_dashboard_v527.py').read_text())
    def test_old_window_removed(self): self.assertNotIn('def open_decision_register()', (ROOT/'campaign_dashboard_v527.py').read_text())
    def test_history_passed(self): self.assertIn('history=history', (ROOT/'campaign_dashboard_v527.py').read_text())
    def test_ui_supports_history(self): self.assertIn('history',open_workspace.__code__.co_varnames)
    def test_actions_include_link(self): self.assertIn("'link'",(ROOT/'decision_workspace_ui_v543.py').read_text())
    def test_actions_include_followup(self): self.assertIn("'followup'",(ROOT/'decision_workspace_ui_v543.py').read_text())
    def test_view_api_retained(self): self.assertTrue(callable(SavedViews))
    def test_search_api_retained(self): self.assertTrue(callable(workspace))
    def test_no_automatic_activation(self): self.assertNotIn('AUTO_REMEDIATE', (ROOT/'decision_workspace_ui_v543.py').read_text())
