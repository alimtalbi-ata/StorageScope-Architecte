"""v6.33 Windows release contract, retained across subsequent releases."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleaseTests(unittest.TestCase):
    def current_version(self):
        current = (ROOT / "07-Manifestes/VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(current, r"^\d+\.\d+$")
        self.assertGreaterEqual(tuple(map(int, current.split("."))), (6, 33))
        return current

    def test_release_version(self):
        self.current_version()

    def test_entrypoint_direct(self):
        s = (ROOT / "Construire-StorageScope.cmd").read_text(encoding="utf-8")
        self.assertIn("build-all-windows.ps1", s)
        self.assertNotIn("xcopy", s.lower())

    def test_stage_contains_tests(self):
        s = (ROOT / "02-Compilation-Windows/build-all-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("04-Tests-et-Qualification/test_*.py", s)

    def test_versions(self):
        current = self.current_version()
        self.assertIn(f"VERSION = '{current}'",
                      (ROOT / "03-Sources/storagescope_windows.py").read_text(encoding="utf-8"))
        self.assertIn(f'#define AppVersion "{current}"',
                      (ROOT / "02-Compilation-Windows/StorageScope.iss").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
