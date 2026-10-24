"""V6.37 release safeguards, compatible with later versioned builds.

Validate the current version and dynamic artifact names instead of demanding
obsolete V6.37 output names. Author: Abdelhalim Talbi.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "02-Compilation-Windows"


def release_version():
    version = (ROOT / "07-Manifestes/VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+", version):
        raise AssertionError(f"Invalid release version: {version!r}")
    return version


class ReleaseTests(unittest.TestCase):
    def test_version(self):
        version = release_version()
        self.assertGreaterEqual(tuple(map(int, version.split("."))), (6, 37))
        source = (ROOT / "03-Sources/storagescope_windows.py").read_text(encoding="utf-8")
        self.assertIn(f"VERSION = '{version}'", source)

    def test_entrypoint(self):
        self.assertIn("build-all-windows.ps1",
                      (ROOT / "Construire-StorageScope.cmd").read_text(encoding="utf-8"))

    def test_stable_preflight(self):
        self.assertTrue((BUILD / "preflight.ps1").is_file())
        wrapper = (BUILD / "build-all-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("preflight.ps1", wrapper)
        self.assertIn("if (-not $?)", wrapper)

    def test_build_artifact_version(self):
        script = (BUILD / "build-engine-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("$releaseVersion = (Get-Content", script)
        self.assertIn("$expectedVersion = $releaseVersion", script)
        self.assertIn('("installer\\StorageScope-Setup-v{0}.exe" -f $releaseVersion)', script)
        self.assertIn('("installer\\release-manifest-v{0}.json" -f $releaseVersion)', script)
        self.assertIn("Get-FileHash", script)

    def test_installer_version(self):
        installer = (BUILD / "StorageScope.iss").read_text(encoding="utf-8")
        self.assertIn(f'#define AppVersion "{release_version()}"', installer)
        self.assertIn("OutputBaseFilename=StorageScope-Setup-v{#AppVersion}", installer)

    def test_diagnostic_stage(self):
        script = (BUILD / "build-all-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("diagnostic stage retained", script)
        self.assertIn("failed-build-logs", script)


if __name__ == "__main__":
    unittest.main()
