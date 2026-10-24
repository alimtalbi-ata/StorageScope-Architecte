"""PowerShell script-call exit status contracts.

A PowerShell script can leave a stale native LASTEXITCODE behind. Check both
PowerShell success and the native code, but reset LASTEXITCODE immediately
before the call so it can never be inherited from an earlier command.
"""
import unittest
from pathlib import Path

R = Path(__file__).resolve().parents[1]


class PowerShellExitTests(unittest.TestCase):
    def test_workflow_script_calls_use_success_flag(self):
        w = (R / ".github/workflows/windows-build.yml").read_text(encoding="utf-8")
        for name in ("Build failed", "Native qualification failed",
                     "Installer smoke test failed", "Portable smoke test failed"):
            self.assertIn(name, w)

    def test_workflow_native_exitcode_checks_are_not_stale(self):
        w = (R / ".github/workflows/windows-build.yml").read_text(encoding="utf-8")
        build = w.split("- name: Build Windows release", 1)[1].split(
            "- name: Qualify native binaries", 1)[0]
        smoke = w.split("- name: Install and uninstall smoke test", 1)[1].split(
            "- name: Run portable Windows smoke test", 1)[0]
        for block, call, guard in (
            (build, "& './02-Compilation-Windows/build-all-windows.ps1'", "Build process returned"),
            (smoke, "& './02-Compilation-Windows/qualify-installer-smoke-windows.ps1'",
             "Installer smoke test returned"),
        ):
            self.assertLess(block.index("$global:LASTEXITCODE = 0"), block.index(call))
            self.assertLess(block.index(call), block.index(guard))
            self.assertIn("if (-not $?)", block)
            self.assertIn("if ($LASTEXITCODE -ne 0)", block)

    def test_build_native_exitcode_checks_are_not_stale(self):
        b = (R / "02-Compilation-Windows/build-all-windows.ps1").read_text(encoding="utf-8")
        preflight = b.split("$global:LASTEXITCODE = 0", 1)[1].split(
            "# Crash-recovery gate", 1)[0]
        self.assertLess(preflight.index("preflight.ps1"), preflight.index("Preflight returned exit code"))
        self.assertIn("if (-not $?)", preflight)
        self.assertIn("if ($LASTEXITCODE -ne 0)", preflight)
        engine = b.split("Push-Location $stage", 1)[1].split(
            "} finally { Pop-Location }", 1)[0]
        self.assertLess(engine.index("$global:LASTEXITCODE = 0"), engine.index("build-engine-windows.ps1"))
        self.assertLess(engine.index("build-engine-windows.ps1"), engine.index("Build engine returned exit code"))
        self.assertIn("if (-not $?)", engine)
        self.assertIn("if ($LASTEXITCODE -ne 0)", engine)

    def test_python_exitcode_checks_retained(self):
        b = (R / "02-Compilation-Windows/build-all-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("Transactional publication failed", b)
        self.assertIn("Validation binary echouee", b)


if __name__ == "__main__":
    unittest.main()
