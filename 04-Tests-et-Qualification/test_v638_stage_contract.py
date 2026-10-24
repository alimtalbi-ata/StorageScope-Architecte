"""V6.38 Windows staging and preflight invariants for later releases.

No static historic version is permitted to bypass current-version consistency.
Author: Abdelhalim Talbi.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "02-Compilation-Windows"


def release_version():
    version = (ROOT / "07-Manifestes/VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+", version):
        raise AssertionError(f"Invalid VERSION: {version!r}")
    return version


class TestStage(unittest.TestCase):
    def test_required_stage_files(self):
        wrapper = (BUILD_DIR / "build-all-windows.ps1").read_text(encoding="utf-8")
        for name in ("Construire-StorageScope.cmd", "qualifier-installation-windows.ps1",
                     "qualifier-executable-windows.ps1", "windows-build.yml"):
            with self.subTest(name=name):
                self.assertIn(name, wrapper)

    def test_version(self):
        version = release_version()
        self.assertGreaterEqual(tuple(map(int, version.split("."))), (6, 38))
        app = (ROOT / "03-Sources/storagescope_windows.py").read_text(encoding="utf-8")
        installer = (BUILD_DIR / "StorageScope.iss").read_text(encoding="utf-8")
        self.assertIn(f"VERSION = '{version}'", app)
        self.assertIn(f'#define AppVersion "{version}"', installer)

    def test_version_build(self):
        script = (BUILD_DIR / "build-engine-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("$releaseVersion = (Get-Content", script)
        self.assertIn("$expectedVersion = $releaseVersion", script)
        self.assertIn("Get-FileHash", script)

    def test_version_preflight(self):
        script = (BUILD_DIR / "preflight.ps1").read_text(encoding="utf-8")
        self.assertIn("07-Manifestes/VERSION", script)
        self.assertIn("$version -notmatch", script)
        self.assertIn("Test-Path", script)
        self.assertIn("throw", script)

    def test_verifier_contract(self):
        verifier = (BUILD_DIR / "verify-windows-build.py").read_text(encoding="utf-8")
        self.assertIn("qualifier-installation-windows.ps1", verifier)
        self.assertIn("Application/release version mismatch", verifier)
        self.assertIn("Inno version mismatch", verifier)


if __name__ == "__main__":
    unittest.main()
