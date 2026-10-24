"""Windows delivery contracts with version-independent, fail-closed checks.

The original V5.85 checks pinned V6.17 and an obsolete inline CI verifier.
The current release uses an independent SHA256 verifier and gated publication.
Author: Abdelhalim Talbi.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


class WindowsCI585(unittest.TestCase):
    def test_manifest_mapping_is_independent(self):
        verifier = read("verify-binary-delivery.py")
        self.assertIn("def validate(folder, version):", verifier)
        self.assertIn("len(set(names))!=len(names)", verifier)
        self.assertIn("set(names)!=expected", verifier)
        self.assertIn("size!=item.get('bytes')", verifier)
        self.assertIn("hashlib.file_digest", verifier)
        self.assertIn("SHA256 mismatch", verifier)
        self.assertIn("is_symlink()", verifier)

    def test_manifest_expected_three_artifacts(self):
        # Current delivery is five payloads plus BINARY-MANIFEST.json.
        verifier = read("verify-binary-delivery.py")
        for filename in ("StorageScope.exe", "StorageScope-UpgradeGate.exe",
                         "StorageScope-Setup-v", "StorageScope-Portable-v",
                         "release-manifest-v"):
            with self.subTest(filename=filename):
                self.assertIn(filename, verifier)
        self.assertIn("len(artifacts)!=len(expected)", verifier)
        self.assertIn("Unexpected files in delivery", verifier)

    def test_upload_paths(self):
        workflow = read(".github/workflows/windows-build.yml")
        self.assertIn("Gate release artifacts on complete qualification", workflow)
        self.assertIn("StorageScope-Windows-QUALIFIED", workflow)
        self.assertIn("binary/v*/**", workflow)
        self.assertIn("if: success()", workflow)
        self.assertIn("StorageScope-Windows-DIAGNOSTICS", workflow)
        self.assertIn("if: always()", workflow)

    def test_installer_qualification_checks_gate(self):
        script = read("qualifier-installation-windows.ps1")
        iss = read("StorageScope.iss")
        self.assertIn("param([string]$Version =", script)
        self.assertIn("07-Manifestes/VERSION", script)
        self.assertIn("Upgrade gate absent apres installation", script)
        self.assertIn('Source: "dist\\StorageScope-UpgradeGate.exe"; Flags: dontcopy', iss)
        self.assertIn('Source: "dist\\StorageScope-UpgradeGate.exe"; DestDir: "{app}"', iss)
        self.assertIn("PrepareToInstall", iss)

    def test_ci_version(self):
        workflow = read(".github/workflows/windows-build.yml")
        engine = read("build-engine-windows.ps1")
        self.assertIn("07-Manifestes/VERSION", workflow)
        self.assertIn("verify-binary-delivery.py", workflow)
        self.assertIn("release-manifest-v{0}.json", engine)
        self.assertIn("StorageScope-Setup-v{0}.exe", engine)
        self.assertIn("StorageScope-Windows-QUALIFIED", workflow)


if __name__ == "__main__":
    unittest.main()
