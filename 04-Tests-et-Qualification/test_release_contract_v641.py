"""v6.41 release contract: version floor and current dynamic packaging."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleaseContractTests(unittest.TestCase):
    def test_manifest(self):
        current = (ROOT / "07-Manifestes/VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(current, r"^\d+\.\d+$")
        self.assertGreaterEqual(tuple(map(int, current.split("."))), (6, 41))

    def test_build_dynamic_version(self):
        s = (ROOT / "02-Compilation-Windows/build-all-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("07-Manifestes/VERSION", s)
        self.assertIn("Setup-v$releaseVersion.exe", s)
        self.assertNotIn("-ne '6.41'", s)

    def test_installed_version_strict(self):
        s = (ROOT / "02-Compilation-Windows/qualify-native-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("$installedVersion -ne $version", s)

    def test_no_recursive_staging(self):
        s = (ROOT / "02-Compilation-Windows/build-all-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("Recursive stage detected", s)


if __name__ == "__main__":
    unittest.main()
