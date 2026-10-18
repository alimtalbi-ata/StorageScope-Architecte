"""Static integration checks; no display needed. Author: Abdelhalim Talbi."""
import ast, unittest
from pathlib import Path
class UITraceabilityTests(unittest.TestCase):
 def test_ui_compiles(self):
  ast.parse(Path(__file__).with_name('desktop.py').read_text(encoding='utf-8'))
 def test_ui_exposes_traceability(self):
  source=Path(__file__).with_name('desktop.py').read_text(encoding='utf-8')
  for token in ('artifact_form','check_closure','export_closure','self.trace.link','self.trace.complete'):
   self.assertIn(token,source)
