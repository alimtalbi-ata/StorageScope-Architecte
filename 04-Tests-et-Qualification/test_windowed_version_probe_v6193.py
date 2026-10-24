"""Prevent asynchronous GUI launch from bypassing the native version probe.

The definitive check runs on Windows CI after PyInstaller; these tests ensure
the process-waiting contract remains wired into the build script.
Author: Abdelhalim Talbi.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WindowedVersionProbeContract(unittest.TestCase):
    def test_windowed_process_is_waited_and_exit_code_checked(self):
        build = (ROOT / "02-Compilation-Windows/build-engine-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("function Invoke-WindowedChecked", build)
        self.assertIn("Start-Process -FilePath $Exe -ArgumentList $Arguments -Wait -PassThru", build)
        self.assertIn("$process.ExitCode -ne 0", build)
        self.assertIn("Invoke-WindowedChecked", build)

    def test_both_frozen_probes_use_synchronous_launch(self):
        build = (ROOT / "02-Compilation-Windows/build-engine-windows.ps1").read_text(encoding="utf-8")
        self.assertIn('Invoke-WindowedChecked "$PSScriptRoot\\dist\\StorageScope.exe" @(\'--self-test\')', build)
        self.assertIn('Invoke-WindowedChecked "$PSScriptRoot\\dist\\StorageScope.exe" @(\'--version-file\'', build)
        self.assertNotIn('Invoke-Checked "$PSScriptRoot\\dist\\StorageScope.exe"', build)
        self.assertIn("EXE version probe not created", build)

    def test_app_writes_requested_version_file(self):
        source = (ROOT / "03-Sources/storagescope_windows.py").read_text(encoding="utf-8")
        self.assertIn("args[0] == '--version-file'", source)
        self.assertIn("Path(args[1]).write_text(VERSION", source)


if __name__ == "__main__":
    unittest.main()
