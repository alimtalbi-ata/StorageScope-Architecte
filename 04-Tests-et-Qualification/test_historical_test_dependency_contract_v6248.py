"""V6.248 regression contract for the historical PNG export dependency.

The original Windows baseline failed test_graph_export.ExportTests.test_png
because Pillow was not installed in the test environment. This test validates
that the dependency is declared, installed by each qualification workflow, and
that PNG export produces a readable image. Author: Abdelhalim Talbi.
"""
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TEST_REQ = ROOT / "04-Tests-et-Qualification" / "requirements-test.txt"
BUILD_REQ = ROOT / "02-Compilation-Windows" / "requirements-build.txt"


def pinned_pillow(path: Path) -> str:
    matches = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.partition("#")[0].strip()
        if line and re.match(r"(?i)^Pillow\s*==", line):
            matches.append(line)
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one pinned Pillow dependency in {path}")
    match = re.fullmatch(r"(?i)Pillow\s*==\s*([A-Za-z0-9_.+-]+)", matches[0])
    if not match:
        raise AssertionError(f"Pillow must be exactly pinned in {path}: {matches[0]!r}")
    return match.group(1)


class HistoricalTestDependencyContractV6248(unittest.TestCase):
    def test_pillow_is_pinned_consistently_for_build_and_tests(self):
        self.assertEqual(pinned_pillow(TEST_REQ), "11.3.0")
        self.assertEqual(pinned_pillow(BUILD_REQ), pinned_pillow(TEST_REQ))

    def test_every_qualification_entrypoint_installs_and_runs_png_regression(self):
        paths = [
            ROOT / ".github" / "workflows" / "windows-build.yml",
            ROOT / ".github" / "workflows" / "governance-review-qualification.yml",
        ]
        for path in paths:
            text = path.read_text(encoding="utf-8")
            if path.name == "governance-review-qualification.yml":
                parts = text.split("  review-windows:", 1)
                self.assertEqual(len(parts), 2, "governance workflow must retain Linux and Windows jobs")
                scopes = [parts[0], "  review-windows:" + parts[1]]
                self.assertEqual(
                    sum("Install explicit test dependencies and replay historical Pillow failure (V6.248)" in scope for scope in scopes),
                    2,
                )
            else:
                scopes = [text]
            for index, scope in enumerate(scopes, start=1):
                with self.subTest(workflow=path.name, job=index):
                    self.assertIn("04-Tests-et-Qualification/requirements-test.txt", scope)
                    self.assertIn("test_graph_export.py", scope)
                    self.assertIn("pip check", scope)
                    self.assertLess(
                        scope.index("04-Tests-et-Qualification/requirements-test.txt"),
                        scope.index("test_graph_export.py"),
                        f"{path.name} must install test requirements before running the PNG regression",
                    )
                    self.assertLess(scope.index("pip check"), scope.index("test_graph_export.py"))
        engine = (ROOT / "02-Compilation-Windows" / "build-engine-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("04-Tests-et-Qualification/requirements-test.txt", engine)
        self.assertLess(engine.index("requirements-test.txt"), engine.index("$historicalRunner"))
        self.assertIn("Invoke-Checked $builder @('-m','pip','check')", engine)

    def test_png_export_generates_a_readable_png_without_skipping(self):
        source = str(ROOT / "03-Sources")
        if source not in sys.path:
            sys.path.insert(0, source)
        from PIL import Image
        from graph_export import export_png

        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "graph.png"
            export_png({"title": "StorageScope qualification", "nodes": [("SAN", "fabric-01", "OK", False)]}, output)
            self.assertTrue(output.is_file())
            self.assertEqual(output.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            with Image.open(output) as image:
                image.verify()


if __name__ == "__main__":
    unittest.main()
