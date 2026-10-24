"""Regression: pre-upgrade extraction is not an installed UpgradeGate.

Static contract only; the Windows CI must also run the real installer smoke.
Author: Abdelhalim Talbi.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "02-Compilation-Windows"


class InstalledUpgradeGateContract(unittest.TestCase):
    def test_inno_both_preflight_and_installed_payload(self):
        iss = (BUILD / "StorageScope.iss").read_text(encoding="utf-8")
        self.assertIn('Source: "dist\\StorageScope-UpgradeGate.exe"; Flags: dontcopy', iss)
        self.assertIn('Source: "dist\\StorageScope-UpgradeGate.exe"; DestDir: "{app}"; Flags: ignoreversion', iss)
        self.assertIn("ExtractTemporaryFile('StorageScope-UpgradeGate.exe')", iss)
        self.assertIn("function PrepareToInstall", iss)

    def test_native_installer_smoke_checks_gate(self):
        smoke = (BUILD / "qualify-installer-smoke-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("$report.gate_checked = $true", smoke)
        self.assertIn("Installed upgrade gate missing", smoke)
        self.assertIn("Installed upgrade gate unexpectedly small", smoke)
        self.assertIn("$report.installed -and $report.gate_checked", smoke)

    def test_ci_fails_without_gate_evidence(self):
        workflow = (ROOT / ".github/workflows/windows-build.yml").read_text(encoding="utf-8")
        self.assertIn("-not $result.gate_checked", workflow)
        self.assertIn("Install and uninstall smoke test", workflow)
        self.assertIn("Gate release artifacts on complete qualification", workflow)


if __name__ == "__main__":
    unittest.main()
