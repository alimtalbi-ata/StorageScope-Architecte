"""Functional contract and source wiring for dashboard quick actions."""
import ast
import unittest
from pathlib import Path
from decision_views_v543 import validate_filters

ROOT=Path(__file__).parent
class DashboardActionsV603(unittest.TestCase):
    def test_initial_filter_is_valid(self):
        d={'query':'','owner':None,'status':'all','deadline':'overdue'}
        self.assertEqual(validate_filters(d)['deadline'],'overdue')
    def test_invalid_filter_is_rejected(self):
        with self.assertRaises(ValueError): validate_filters({'query':'','owner':None,'status':'all','deadline':'tomorrow'})
    def test_dashboard_has_three_shortcuts(self):
        s=(ROOT/'storagescope_windows.py').read_text()
        for label in ('Voir les retards','Voir les décisions','Voir les campagnes'):
            self.assertIn(label,s)
    def test_overdue_filter_applies_on_existing_page(self):
        s=(ROOT/'storagescope_windows.py').read_text()
        self.assertIn("governance_refresh['callback']({'deadline': deadline})",s)
    def test_workspace_accepts_validated_initial_filters(self):
        s=(ROOT/'decision_workspace_ui_v543.py').read_text()
        self.assertIn('initial = validate_filters(defaults)',s)
        self.assertIn('validated = validate_filters(current)',s)
    def test_python_syntax(self):
        for filename in ('storagescope_windows.py','decision_workspace_ui_v543.py'):
            ast.parse((ROOT/filename).read_text())
