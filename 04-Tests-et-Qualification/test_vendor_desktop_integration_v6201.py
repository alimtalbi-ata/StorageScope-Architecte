"""Desktop integration regression for offline NAS vendor review."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '03-Sources' / 'storagescope_windows.py'


class VendorDesktopIntegrationTests(unittest.TestCase):
    def test_vendor_import_is_reachable_from_diagnostic_page(self):
        source = SOURCE.read_text(encoding='utf-8')
        tree = ast.parse(source)
        launch = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'launch')
        diagnostics = next(node for node in ast.walk(launch) if isinstance(node, ast.FunctionDef) and node.name == 'diagnostics')
        handler = next(node for node in ast.walk(diagnostics) if isinstance(node, ast.FunctionDef) and node.name == 'review_vendor_snapshot')
        calls = [node for node in ast.walk(handler) if isinstance(node, ast.Call)]
        names = [node.func.id for node in calls if isinstance(node.func, ast.Name)]
        self.assertIn('load_snapshot', names)
        self.assertIn('normalize', names)
        self.assertIn('showerror', [node.func.attr for node in calls if isinstance(node.func, ast.Attribute)])
        self.assertIn('review_vendor_snapshot', source)
        self.assertIn('Importer un inventaire NetApp / PowerScale / FlashBlade', source)

    def test_vendor_report_remains_observational(self):
        source = SOURCE.read_text(encoding='utf-8')
        handler = source.split('        def review_vendor_snapshot():', 1)[1].split('        ttk.Button(page, text=', 1)[0]
        self.assertIn('Aucune modification de la CMDB ou des équipements.', handler)
        self.assertNotIn('sqlite3.connect', handler)
        self.assertNotIn('subprocess.', handler)


if __name__ == '__main__':
    unittest.main()
