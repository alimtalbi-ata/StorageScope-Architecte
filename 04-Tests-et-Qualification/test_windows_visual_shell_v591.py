"""Static checks for visual navigation without requiring a display."""
import unittest
from pathlib import Path

SOURCE = (Path(__file__).parent / 'storagescope_windows.py').read_text(encoding='utf-8')

class VisualShellTests(unittest.TestCase):
    def test_visual_hierarchy(self):
        self.assertIn('Hero.TLabel', SOURCE)
        self.assertIn('Section.TLabel', SOURCE)
    def test_sidebar_shortcuts(self):
        self.assertIn('AIDE ET RACCOURCIS', SOURCE)
        self.assertIn('Ctrl+F  Rechercher', SOURCE)
    def test_keyboard_navigation(self):
        self.assertIn('<Alt-Left>', SOURCE)
    def test_unused_state_removed(self):
        self.assertNotIn('campaigns_loaded', SOURCE)
    def test_author_credit(self):
        self.assertIn('Abdelhalim Talbi · v', SOURCE)
