"""Tests for conservative static component inventory."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"tools"/"audit_component_inventory.py"
spec=importlib.util.spec_from_file_location("audit_component_inventory",P)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class ComponentInventoryTests(unittest.TestCase):
    def test_detects_imports_and_unreferenced_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"storagescope_windows.py").write_text("import helper\ndef main(): pass\n")
            (root/"helper.py").write_text("class Worker: pass\n")
            (root/"unused.py").write_text("def work(): pass\n")
            report=module.inventory(root)
            self.assertEqual(report["source_files"],3)
            self.assertIn("unused",report["potentially_unreferenced_modules"])
            self.assertNotIn("helper",report["potentially_unreferenced_modules"])
    def test_does_not_delete_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);file=root/"sample.py";file.write_text("pass\n")
            module.inventory(root)
            self.assertTrue(file.exists())
if __name__=="__main__":unittest.main()
