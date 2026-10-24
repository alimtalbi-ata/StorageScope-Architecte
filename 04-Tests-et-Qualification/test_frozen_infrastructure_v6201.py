"""Windows frozen-build inclusion gate for the Infrastructure workspace.

Does not claim that a human has interacted with the GUI.
"""
import ast
import sys
import unittest
from pathlib import Path

SOURCES = Path(__file__).resolve().parents[1] / '03-Sources'
sys.path.insert(0, str(SOURCES))
from windows_module_inventory import reachable_modules


class FrozenInfrastructureTests(unittest.TestCase):
    def test_vendor_and_inventory_code_reachable_from_windows_executable(self):
        included = set(reachable_modules(SOURCES))
        self.assertIn('vendor_snapshot_import_v6201', included)
        self.assertIn('nas_inventory_desktop_v6201', included)

    def test_infrastructure_navigation_and_workflow_registered(self):
        source = (SOURCES / 'storagescope_windows.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        self.assertIn("'Infrastructure'", source)
        self.assertIn("pages['Infrastructure'] = infrastructure()", source)
        self.assertIn('tree.bind', source)
        self.assertIn('export_inventory_csv as write_inventory_csv', source)
        self.assertIn('inventory_rows(report)', source)
        self.assertTrue(any(isinstance(node, ast.FunctionDef) and node.name == 'launch'
                            for node in tree.body))


if __name__ == '__main__':
    unittest.main()
