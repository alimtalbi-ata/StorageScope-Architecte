"""Regression tests for the static Windows navigation audit."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "audit_ui_navigation.py"
spec = importlib.util.spec_from_file_location("audit_ui_navigation", TOOL)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class NavigationAuditTests(unittest.TestCase):
    def test_duplicate_root_binding_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "app.py"
            file.write_text("def main(): pass\ndef launch(): pass\nroot.bind('<F5>', foo)\nroot.bind('<F5>', bar)\n", encoding="utf-8")
            report = module.audit(file)
            self.assertTrue(any("Duplicate root bindings" in issue for issue in report["issues"]))
    def test_distinct_bindings_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "app.py"
            file.write_text("def main(): pass\ndef launch(): pass\nroot.bind('<F5>', foo)\nroot.bind('<F6>', bar)\n", encoding="utf-8")
            self.assertEqual(module.audit(file)["issues"], [])

if __name__ == "__main__":
    unittest.main()
