"""v6.88 binary publication safeguards, valid for all later versions."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "02-Compilation-Windows/build-all-windows.ps1").read_text(encoding="utf-8")


class Tests(unittest.TestCase):
    def test_upgrade_gate(self):
        self.assertIn("Target='StorageScope-UpgradeGate.exe'", SCRIPT)

    def test_early_version_gate(self):
        self.assertLess(SCRIPT.index("if (Test-Path -LiteralPath $binaryVersionDir)"),
                        SCRIPT.index("& (Join-Path $PSScriptRoot 'preflight.ps1')"))

    def test_staging_preserved(self):
        self.assertIn("Publication binary interrompue", SCRIPT)
        self.assertNotIn("Remove-Item -LiteralPath $binaryStage -Recurse -Force", SCRIPT)

    def test_no_fake_binaries(self):
        self.assertFalse(list((ROOT / "binary").rglob("*.exe")))

    def test_version(self):
        current = (ROOT / "07-Manifestes/VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(current, r"^\d+\.\d+$")
        self.assertGreaterEqual(tuple(map(int, current.split("."))), (6, 88),
                                "The v6.88 publication contract must not regress")


if __name__ == "__main__":
    unittest.main()
