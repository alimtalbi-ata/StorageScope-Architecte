"""Binary delivery regression: preserve v6.87 guarantees across newer releases."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BinaryDeliveryTests(unittest.TestCase):
    def test_native_build_outputs(self):
        s = (ROOT / "02-Compilation-Windows/build-all-windows.ps1").read_text(encoding="utf-8")
        for item in ("StorageScope.exe", "StorageScope-Setup-v$releaseVersion.exe",
                     "StorageScope-Portable-v$releaseVersion-win-x64.zip",
                     "BINARY-MANIFEST.json", "Get-FileHash", "Move-Item"):
            with self.subTest(item=item):
                self.assertIn(item, s)

    def test_version(self):
        current = (ROOT / "07-Manifestes/VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(current, r"^\d+\.\d+$")
        self.assertGreaterEqual(tuple(map(int, current.split("."))), (6, 87),
                                "The v6.87 binary-delivery contract must not regress")

    def test_no_fake_exe(self):
        self.assertEqual(list((ROOT / "binary").rglob("*.exe")), [])

    def test_binary_folder(self):
        self.assertTrue((ROOT / "binary/README.txt").is_file())


if __name__ == "__main__":
    unittest.main()
