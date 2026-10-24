"""Desktop integration regression; keep V6.29 behavior in later releases."""
import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "03-Sources"))
import storagescope_windows as app
import governance_desktop as gd


class IntegrationTests(unittest.TestCase):
    def test_version(self):
        release = (ROOT / "07-Manifestes/VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(release, r"^\d+\.\d+$")
        self.assertGreaterEqual(tuple(map(int, release.split("."))), (6, 29))
        self.assertEqual(app.VERSION, release)

    def test_launch_parent_contract(self):
        self.assertIn("parent", gd.launch.__code__.co_varnames)

    def test_embedded_navigation(self):
        source = Path(app.__file__).read_text(encoding="utf-8")
        self.assertIn("command=open_inventory_review", source)
        self.assertIn("launch_inventory_review(parent=root)", source)

    def test_syntax_all(self):
        base = Path(app.__file__).parent
        for source in base.glob("*.py"):
            with self.subTest(file=source.name):
                ast.parse(source.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
