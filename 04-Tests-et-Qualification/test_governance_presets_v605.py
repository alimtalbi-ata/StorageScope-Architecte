import unittest
from pathlib import Path
SOURCE = (Path(__file__).parent / 'decision_workspace_ui_v543.py').read_text(encoding='utf-8')
class GovernancePresets(unittest.TestCase):
    def test_preset_resets_search(self): self.assertIn("query.set(''); owner.set(''); status.set(selected_status); deadline.set(selected_deadline)", SOURCE)
    def test_overdue_preset(self): self.assertIn("preset(selected_deadline='overdue')", SOURCE)
    def test_today_preset(self): self.assertIn("preset(selected_deadline='due_today')", SOURCE)
    def test_review_preset(self): self.assertIn("preset(selected_status='IN_REVIEW')", SOURCE)
    def test_distinct_saved_view_selection(self): self.assertIn('selected_view = tk.StringVar()', SOURCE); self.assertIn('saved.load()[selected_view.get()]', SOURCE)
    def test_saved_view_delete_selection(self): self.assertIn('saved.delete(selected_view.get())', SOURCE)
