import unittest
from pathlib import Path

class NavigationErrorsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(__file__).with_name('storagescope_windows.py').read_text()
    def test_shared_error_boundary(self):
        self.assertIn('def navigate_safely(name):', self.source)
        self.assertIn("messagebox.showerror('Ouverture de ' + name", self.source)
    def test_search_uses_boundary(self):
        self.assertIn('navigate_safely(destination)', self.source)
    def test_sidebar_uses_boundary(self):
        self.assertIn('lambda n=name: navigate_safely(n)', self.source)
    def test_keyboard_uses_boundary(self):
        self.assertIn("lambda event: navigate_safely('Accueil')", self.source)
    def test_governance_campaigns_use_boundary(self):
        self.assertIn("opened = navigate_safely('Gouvernance')", self.source)
        self.assertIn("return navigate_safely('Campagnes')", self.source)
