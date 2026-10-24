"""Regression: installer rejection gate must preserve the GitHub Actions caller cwd.

The gate's own report paths are anchored to PSScriptRoot, whereas the workflow
reads its evidence relative to the repository root. A Set-Location in the gate
caused a false missing-evidence failure after a successful rejection.
Author: Abdelhalim Talbi.
"""
import pathlib
import shutil
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "02-Compilation-Windows" / "qualifier-echec-installateur-windows.ps1"
WORKFLOW = ROOT / ".github" / "workflows" / "windows-build.yml"


class InstallerRejectionCwdRegression(unittest.TestCase):
    def test_gate_uses_absolute_script_relative_evidence_paths(self):
        source = SCRIPT.read_text(encoding="utf-8-sig")
        self.assertNotRegex(source, r"(?im)^\s*Set-Location\b")
        self.assertIn("$logDir = Join-Path $PSScriptRoot 'build-logs'", source)
        self.assertIn("$report = Join-Path $logDir", source)
        self.assertIn("Set-Content -LiteralPath $report", source)

    def test_workflow_requires_actual_rejection_evidence(self):
        workflow = WORKFLOW.read_text(encoding="utf-8-sig")
        self.assertIn("qualifier-echec-installateur-windows.ps1", workflow)
        self.assertIn("installer-rejected-v{0}.json", workflow)
        self.assertIn("Installer rejection evidence missing", workflow)
        self.assertIn("$rejection.source_unchanged", workflow)
        self.assertIn("$rejection.installed_binary_present", workflow)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell 7 unavailable: static contracts still tested")
    def test_gate_preserves_cwd_on_missing_installer(self):
        # An impossible version fails before creating any user data or launching setup.
        script = str(SCRIPT).replace("'", "''")
        command = (
            "$before=(Get-Location).Path; $rejected=$false; "
            f"try {{ & '{script}' -Version '0.0-missing-cwd-regression' }} "
            "catch { $rejected=($_.Exception.Message -like '*Installateur absent*') }; "
            "if (-not $rejected) { exit 3 }; "
            "if ((Get-Location).Path -ne $before) { exit 4 }; exit 0"
        )
        result = subprocess.run(
            ["pwsh", "-NoProfile", "-NonInteractive", "-Command", command],
            cwd=ROOT, capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
