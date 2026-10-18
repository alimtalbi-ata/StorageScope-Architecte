import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class BinaryDeliveryTests(unittest.TestCase):
    def test_native_build_outputs(self):
        s=(ROOT/'02-Compilation-Windows/build-all-windows.ps1').read_text(encoding='utf-8')
        for item in ('StorageScope.exe','StorageScope-Setup-v$releaseVersion.exe','StorageScope-Portable-v$releaseVersion-win-x64.zip','BINARY-MANIFEST.json','Get-FileHash','Move-Item'):
            self.assertIn(item,s)
    def test_version(self):
        self.assertEqual((ROOT/'07-Manifestes/VERSION').read_text().strip(),'6.87')
    def test_no_fake_exe(self):
        self.assertEqual(list((ROOT/'binary').rglob('*.exe')),[])
    def test_binary_folder(self):
        self.assertTrue((ROOT/'binary/README.txt').is_file())
if __name__=="__main__": unittest.main()
