import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
class TabbedCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui = (ROOT/'campaign_dashboard_v527.py').read_text()
        cls.build = (ROOT/'build-all-windows.ps1').read_text()
    def test_notebook(self): self.assertIn('notebook = ttk.Notebook(root)', self.ui)
    def test_three_tabs(self):
        for name in ('Historique', 'Comparer et exporter', 'Alertes et revue'):
            self.assertIn("text='"+name+"'", self.ui)
    def test_history_parent(self): self.assertIn('table_frame = ttk.Frame(history_tab)', self.ui)
    def test_compare_parent(self): self.assertIn('comparison = ttk.LabelFrame(comparison_tab', self.ui)
    def test_review_parent(self): self.assertIn('alert_controls = ttk.Frame(review_tab', self.ui)
    def test_builder_version(self):
        engine=(ROOT/'build-engine-windows.ps1').read_text(encoding='utf-8')
        self.assertIn("$releaseVersion = (Get-Content",self.build)
        self.assertIn('$expectedVersion = $releaseVersion',engine)
        self.assertNotIn('v5.70.exe', self.build)
    def test_inno_version(self):
        release=(ROOT/'VERSION').read_text(encoding='utf-8').strip()
        self.assertIn(f'#define AppVersion "{release}"',(ROOT/'StorageScope.iss').read_text(encoding='utf-8'))
if __name__ == '__main__': unittest.main()
