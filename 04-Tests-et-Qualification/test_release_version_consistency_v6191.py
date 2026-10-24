"""Current release version consistency and tampering regressions.

These checks retain the historical release floor while requiring the *current*
VERSION, Python application and Inno Setup installer to agree. They do not
modify or skip any historical test. Author: Abdelhalim Talbi.
"""
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
VERSION_PATTERN = re.compile(r"\d+\.\d+")
APP_VERSION_PATTERN = re.compile(r"(?m)^VERSION\s*=\s*['\"]([^'\"]+)['\"]\s*$")
INSTALLER_VERSION_PATTERN = re.compile(r'(?m)^#define AppVersion "([^"]+)"\s*$')


def check_release_contract(root: Path) -> str:
    """Fail closed on missing, duplicated, malformed or mismatched versions."""
    root = Path(root)
    version = (root / "07-Manifestes/VERSION").read_text(encoding="utf-8").strip()
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError("Invalid canonical VERSION")
    if tuple(map(int, version.split("."))) < (6, 108):
        raise ValueError("Release version regressed below v6.108")
    source = (root / "03-Sources/storagescope_windows.py").read_text(encoding="utf-8")
    installer = (root / "02-Compilation-Windows/StorageScope.iss").read_text(encoding="utf-8")
    build = (root / "02-Compilation-Windows/build-all-windows.ps1").read_text(encoding="utf-8")
    engine = (root / "02-Compilation-Windows/build-engine-windows.ps1").read_text(encoding="utf-8")
    app_matches = APP_VERSION_PATTERN.findall(source)
    installer_matches = INSTALLER_VERSION_PATTERN.findall(installer)
    if app_matches != [version]:
        raise ValueError("Python application VERSION differs from canonical VERSION")
    if installer_matches != [version]:
        raise ValueError("Inno Setup AppVersion differs from canonical VERSION")
    if ("$releaseVersion = (Get-Content" not in build
            or "07-Manifestes/VERSION" not in build
            or "StorageScope-Setup-v$releaseVersion.exe" not in build
            or "$expectedVersion = $releaseVersion" not in engine):
        raise ValueError("Windows build must derive its version from the canonical manifest")
    return version


class ReleaseConsistencyV6191Tests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="storagescope-version-contract-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.write("07-Manifestes/VERSION", "6.108\n")
        self.write("03-Sources/storagescope_windows.py", "VERSION = '6.108'\n")
        self.write("02-Compilation-Windows/StorageScope.iss", '#define AppVersion "6.108"\n')
        self.write("02-Compilation-Windows/build-all-windows.ps1",
                   "$releaseVersion = (Get-Content (Join-Path $root '07-Manifestes/VERSION') -Raw).Trim()\n"
                   'StorageScope-Setup-v$releaseVersion.exe\n')
        self.write("02-Compilation-Windows/build-engine-windows.ps1",
                   "$expectedVersion = $releaseVersion\n")

    def write(self, relative, data):
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data, encoding="utf-8")

    def test_real_checkout_current_versions_agree(self):
        self.assertEqual(check_release_contract(ROOT),
                         (ROOT / "07-Manifestes/VERSION").read_text(encoding="utf-8").strip())

    def test_matching_fixture_is_accepted(self):
        self.assertEqual(check_release_contract(self.root), "6.108")

    def test_source_version_mismatch_rejected(self):
        self.write("03-Sources/storagescope_windows.py", "VERSION = '6.107'\n")
        with self.assertRaisesRegex(ValueError, "Python application"):
            check_release_contract(self.root)

    def test_installer_version_mismatch_rejected(self):
        self.write("02-Compilation-Windows/StorageScope.iss", '#define AppVersion "6.109"\n')
        with self.assertRaisesRegex(ValueError, "Inno Setup"):
            check_release_contract(self.root)

    def test_duplicate_installer_define_rejected(self):
        self.write("02-Compilation-Windows/StorageScope.iss",
                   '#define AppVersion "6.108"\n#define AppVersion "6.108"\n')
        with self.assertRaisesRegex(ValueError, "Inno Setup"):
            check_release_contract(self.root)

    def test_duplicate_python_version_rejected(self):
        self.write("03-Sources/storagescope_windows.py", "VERSION = '6.108'\nVERSION = '6.108'\n")
        with self.assertRaisesRegex(ValueError, "Python application"):
            check_release_contract(self.root)

    def test_hardcoded_build_version_rejected(self):
        self.write("02-Compilation-Windows/build-engine-windows.ps1", "$expectedVersion = '6.108'\n")
        with self.assertRaisesRegex(ValueError, "Windows build"):
            check_release_contract(self.root)

    def test_version_rollback_rejected(self):
        self.write("07-Manifestes/VERSION", "6.87\n")
        with self.assertRaisesRegex(ValueError, "regressed"):
            check_release_contract(self.root)

    def test_invalid_version_rejected(self):
        self.write("07-Manifestes/VERSION", "6.108-beta\n")
        with self.assertRaisesRegex(ValueError, "Invalid canonical"):
            check_release_contract(self.root)

    def test_missing_installer_rejected(self):
        (self.root / "02-Compilation-Windows/StorageScope.iss").unlink()
        with self.assertRaises(FileNotFoundError):
            check_release_contract(self.root)


if __name__ == "__main__":
    unittest.main()
