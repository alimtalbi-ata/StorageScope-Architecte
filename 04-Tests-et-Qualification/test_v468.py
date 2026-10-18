import unittest
from pathlib import Path

class DesktopIntegration(unittest.TestCase):
 def test_cursor_ui_wired(self):
  s=(Path(__file__).parent/'desktop.py').read_text()
  for fragment in ('load_portfolio_readonly','self.cursor_history','self.cursor_index','Navigation rapide','reset_portfolio_navigation'):
   self.assertIn(fragment,s)
 def test_cursor_navigation_guards(self):
  s=(Path(__file__).parent/'desktop.py').read_text()
  self.assertIn("self.portfolio_sort.get()!='id'",s)
  self.assertIn("self.cursor_history=self.cursor_history[:self.cursor_index+1]+[self.cursor_next]",s)
 def test_default_is_full_metrics(self):
  s=(Path(__file__).parent/'desktop.py').read_text()
  self.assertIn('self.cursor_mode=tk.BooleanVar(value=False)',s)
  self.assertIn("self._start_portfolio_worker('filtered'",s)
if __name__=='__main__':unittest.main()
