import ast, pathlib, unittest
from windows_accessibility_v617 import display_metrics
BASE=pathlib.Path(__file__).resolve().parent
class UIContractTests(unittest.TestCase):
 def test_missing_import_regression(self):
  text=(BASE/'storagescope_windows.py').read_text(encoding='utf8')
  self.assertIn('from windows_accessibility_v617 import display_metrics',text)
  self.assertTrue((BASE/'windows_accessibility_v617.py').exists())
 def test_dpi_200_percent_compact(self):
  self.assertTrue(display_metrics(1920,1080,2)['compact'])
 def test_dpi_100_percent_regular(self):
  self.assertFalse(display_metrics(1920,1080,1)['compact'])
 def test_invalid_dpi(self):
  for value in (0,True,5,'2'):
   with self.subTest(value=value),self.assertRaises(ValueError):display_metrics(1920,1080,value)
 def test_tiny_resolution_rejected(self):
  with self.assertRaises(ValueError):display_metrics(100,100)
 def test_module_syntax(self):
  for name in ('storagescope_windows.py','async_portfolio.py','windows_accessibility_v617.py'):
   ast.parse((BASE/name).read_text(encoding='utf8'))
