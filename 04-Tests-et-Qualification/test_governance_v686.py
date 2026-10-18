import unittest
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / '03-Sources' / 'governance_desktop.py').read_text(encoding='utf-8')

class DesktopUXTests(unittest.TestCase):
    def test_version_is_current(self):
        self.assertIn('Revue humaine v6.86', SOURCE)
        self.assertNotIn('Revue humaine v6.73', SOURCE)
    def test_keyboard_navigation_is_table_scoped(self):
        self.assertIn("table.bind('<Prior>'", SOURCE)
        self.assertIn("table.bind('<Next>'", SOURCE)
        self.assertIn("root.bind('<Control-f>', focus_search)", SOURCE)
    def test_pager_disables_unavailable_actions(self):
        self.assertIn("previous_button.configure(state='normal' if report_state['page'] > 0 else 'disabled')", SOURCE)
        self.assertIn("next_button.configure(state='normal' if report_state['page'] < max_page else 'disabled')", SOURCE)
    def test_load_cancels_pending_search(self):
        self.assertIn("def load():\n        if pending_refresh['id'] is not None:", SOURCE)

if __name__ == '__main__': unittest.main()
