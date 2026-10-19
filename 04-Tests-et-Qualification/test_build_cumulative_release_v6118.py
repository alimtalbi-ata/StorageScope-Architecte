"""Tests for single-checkout cumulative release packaging."""
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
P = Path(__file__).resolve().parents[1] / "tools" / "build_cumulative_release.py"
spec = importlib.util.spec_from_file_location("build_cumulative_release", P)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
class BuildCumulativeReleaseTests(unittest.TestCase):
    def prepare(self, root):
        for name in module.VERSIONS:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("6.118\n", encoding="utf-8")
        (root / "03-Sources" / "sample.py").write_text("print('ok')\n", encoding="utf-8")
    def test_source_candidate_has_verified_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"src";root.mkdir();self.prepare(root)
            archive=Path(tmp)/"candidate.zip"
            result=module.build(root,archive,require_windows=False)
            self.assertEqual(result["version"],"6.118")
            with zipfile.ZipFile(archive) as z:
                manifest=json.loads(z.read("07-Manifestes/SHA256-v6.118.json"))
                self.assertIn("03-Sources/sample.py",manifest)
                self.assertIsNone(z.testzip())
    def test_missing_qualification_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"src";root.mkdir();self.prepare(root)
            with self.assertRaises(FileNotFoundError):
                module.build(root,Path(tmp)/"out.zip",require_windows=True)
    def test_mismatched_version_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"src";root.mkdir();self.prepare(root)
            (root / module.VERSIONS[0]).write_text("6.117")
            with self.assertRaisesRegex(ValueError,"disagree"):
                module.build(root,Path(tmp)/"out.zip",require_windows=False)
if __name__ == "__main__":unittest.main()
