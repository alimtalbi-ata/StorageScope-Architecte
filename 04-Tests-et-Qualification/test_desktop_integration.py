import ast
import unittest
from pathlib import Path
class DesktopIntegrationTests(unittest.TestCase):
    def test_desktop_syntax(self):
        ast.parse((Path(__file__).parent/'desktop.py').read_text(encoding='utf-8'))
    def test_desktop_has_expected_commands(self):
        s=(Path(__file__).parent/'desktop.py').read_text(encoding='utf-8')
        for method in ('refresh','export','audit','decision_form','reservation_form','shutdown'):
            self.assertIn('def '+method+'(',s)
if __name__=='__main__':unittest.main()
