"""UI integration regression checks, safe without a display."""
import unittest
from pathlib import Path
ROOT = Path(__file__).parent
G = (ROOT / 'decision_workspace_ui_v543.py').read_text(encoding='utf-8')
C = (ROOT / 'campaign_dashboard_v527.py').read_text(encoding='utf-8')
class WorkspaceUsabilityTests(unittest.TestCase):
    def test_governance_separate_filter_rows(self):
        self.assertIn("search_row = ttk.Frame(controls)", G)
        self.assertIn("filter_row = ttk.Frame(controls)", G)
    def test_governance_reset_in_filter_row(self):
        self.assertIn("ttk.Button(filter_row, text='Effacer les filtres'", G)
    def test_governance_refresh_in_filter_row(self):
        self.assertIn("ttk.Button(filter_row,text='Actualiser'", G)
    def test_campaign_localized_labels(self):
        for label in ('Nœuds','Modifications','Espacement'):
            self.assertIn(label, C)
    def test_campaign_keyboard_and_reset(self):
        self.assertIn("entry.bind('<Return>'", C)
        self.assertIn("text='Effacer les filtres'", C)
