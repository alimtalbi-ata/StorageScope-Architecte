"""Release version consistency tests (stdlib)."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "03-Sources" / "release_version_guard.py"
spec = importlib.util.spec_from_file_location("release_version_guard", SOURCE)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

class ReleaseGuardTests(unittest.TestCase):
    def test_repository_versions_match(self):
        self.assertRegex(guard.check_release_versions(), r"^\d+\.\d+$")

    def test_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in guard.FILES:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("6.108\n", encoding="utf-8")
            script = root / "02-Compilation-Windows/StorageScope.iss"
            script.parent.mkdir(parents=True, exist_ok=True)
            script.write_text('#define AppVersion "6.115"\n', encoding="utf-8")
            app = root / "03-Sources/storagescope_windows.py"
            app.write_text("VERSION = '6.108'\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Version drift"):
                guard.check_release_versions(root)

if __name__ == "__main__":
    unittest.main()
