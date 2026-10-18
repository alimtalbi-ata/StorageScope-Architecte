import ast
import pathlib
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / '03-Sources'))
import storagescope_windows as app
import governance_desktop as gd

class IntegrationTests(unittest.TestCase):
    def test_version(self): self.assertEqual(app.VERSION, '6.29')
    def test_launch_parent_contract(self): self.assertIn('parent', gd.launch.__code__.co_varnames)
    def test_embedded_navigation(self):
        source = pathlib.Path(app.__file__).read_text(encoding='utf-8')
        self.assertIn('command=open_inventory_review', source)
        self.assertIn('launch_inventory_review(parent=root)', source)
    def test_syntax_all(self):
        base = pathlib.Path(app.__file__).parent
        for f in base.glob('*.py'):
            with self.subTest(file=f.name): ast.parse(f.read_text(encoding='utf-8'))
if __name__=='__main__': unittest.main()
