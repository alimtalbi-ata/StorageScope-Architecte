"""Historical v6.35 release invariants, valid for subsequent versions.

These checks must validate current release consistency instead of demanding
that an old, superseded release number remains the active product version.
"""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILD = ROOT / "02-Compilation-Windows"


class ReleaseContract(unittest.TestCase):
    def test_version(self):
        version = (ROOT / "07-Manifestes/VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(version, r"^\d+\.\d+$")
        self.assertGreaterEqual(tuple(map(int, version.split("."))), (6, 35))
        self.assertEqual(
            version,
            (ROOT / "03-Sources/VERSION").read_text(encoding="utf-8").strip(),
            "Source and release manifest versions must agree",
        )
        inno = (BUILD / "StorageScope.iss").read_text(encoding="utf-8")
        self.assertIn(f'#define AppVersion "{version}"', inno)

    def test_scripts(self):
        for name in (
            "build-all-windows.ps1",
            "build-engine-windows.ps1",
            "StorageScope.iss",
            "preflight.ps1",
        ):
            self.assertTrue((BUILD / name).is_file(), name)

    def test_preflight_fails_closed(self):
        preflight = (BUILD / "preflight.ps1").read_text(encoding="utf-8")
        self.assertIn("07-Manifestes/VERSION", preflight)
        self.assertIn("Version inattendue", preflight)
        self.assertIn("Fichier requis absent", preflight)
        self.assertIn("throw", preflight)

    def test_launcher(self):
        launcher = (ROOT / "Construire-StorageScope.cmd").read_text(encoding="utf-8")
        self.assertIn("build-all-windows.ps1", launcher)

    def test_no_stale_build_version(self):
        for name in ("build-all-windows.ps1", "build-engine-windows.ps1", "StorageScope.iss"):
            self.assertNotIn("6.34", (BUILD / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
