"""Tests de filtrage aujourd'hui et des libellés. Auteur : Abdelhalim Talbi."""
import unittest
from pathlib import Path
from decision_views_v543 import validate_filters
from decision_committee_v538 import STATES
ROOT=Path(__file__).parent
class DashboardTodayV604(unittest.TestCase):
    def test_today_is_valid_saved_filter(self):
        self.assertEqual(validate_filters({'query':'','owner':None,'status':'all','deadline':'due_today'})['deadline'],'due_today')
    def test_today_supported_by_business_model(self):
        self.assertIn('due_today',STATES)
    def test_today_action_on_dashboard(self):
        self.assertIn('Voir les échéances du jour', (ROOT/'storagescope_windows.py').read_text())
    def test_today_allowed_for_navigation(self):
        self.assertIn("deadline not in ('overdue', 'due_today')",(ROOT/'storagescope_windows.py').read_text())
    def test_keyboard_enter_works_in_nested_filter_rows(self):
        self.assertIn('for row in (search_row, filter_row):',(ROOT/'decision_workspace_ui_v543.py').read_text())
    def test_friendly_column_labels(self):
        s=(ROOT/'decision_workspace_ui_v543.py').read_text()
        self.assertIn("'evidence_reference':'Référence de preuve'",s)
