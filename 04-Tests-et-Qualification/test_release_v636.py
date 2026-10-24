"""V6.36 release guarantees retained for every subsequent Windows release.

Historical version numbers are minimum supported versions, not a request to
downgrade a newer release. Keep source, manifest and installer in lockstep.
Author: Abdelhalim Talbi.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def current_version():
    value = (ROOT / "07-Manifestes/VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+", value):
        raise AssertionError(f"Invalid release version: {value!r}")
    return value


class ReleaseContracts(unittest.TestCase):
    def test_version(self):
        version = current_version()
        self.assertGreaterEqual(tuple(map(int, version.split("."))), (6, 36))
        source = (ROOT / "03-Sources/storagescope_windows.py").read_text(encoding="utf-8")
        self.assertRegex(source, rf"(?m)^VERSION = ['\"]{re.escape(version)}['\"]$")
        installer = (ROOT / "02-Compilation-Windows/StorageScope.iss").read_text(encoding="utf-8")
        self.assertIn(f'#define AppVersion "{version}"', installer)

    def test_stage_inputs(self):
        stage = (ROOT / "02-Compilation-Windows/build-all-windows.ps1").read_text(encoding="utf-8")
        for name in ("StorageScope.spec", "StorageScope.iss",
                     "requirements-build.txt", "verify-windows-build.py"):
            with self.subTest(name=name):
                self.assertIn(name, stage)

    def test_preflight(self):
        preflight = ROOT / "02-Compilation-Windows/preflight.ps1"
        self.assertTrue(preflight.is_file(), "Stable Windows preflight missing")
        source = preflight.read_text(encoding="utf-8")
        self.assertIn("07-Manifestes/VERSION", source)
        self.assertIn("Test-Path", source)
        self.assertIn("throw", source)
        wrapper = (ROOT / "02-Compilation-Windows/build-all-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("preflight.ps1", wrapper)

    def test_installer_version(self):
        version = current_version()
        installer = (ROOT / "02-Compilation-Windows/StorageScope.iss").read_text(encoding="utf-8")
        self.assertIn(f'#define AppVersion "{version}"', installer)
        self.assertIn("AppVersion={#AppVersion}", installer)


if __name__ == "__main__":
    unittest.main()
