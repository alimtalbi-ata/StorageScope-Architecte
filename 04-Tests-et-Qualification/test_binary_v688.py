import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCRIPT=(ROOT/'02-Compilation-Windows/build-all-windows.ps1').read_text(encoding='utf-8')
class Tests(unittest.TestCase):
 def test_upgrade_gate(self): self.assertIn("Target='StorageScope-UpgradeGate.exe'",SCRIPT)
 def test_early_version_gate(self): self.assertLess(SCRIPT.index('if (Test-Path -LiteralPath $binaryVersionDir)'),SCRIPT.index("& (Join-Path $PSScriptRoot 'preflight.ps1')"))
 def test_staging_preserved(self):
  self.assertIn('Publication binary interrompue',SCRIPT)
  self.assertNotIn('Remove-Item -LiteralPath $binaryStage -Recurse -Force',SCRIPT)
 def test_no_fake_binaries(self): self.assertFalse(list((ROOT/'binary').rglob('*.exe')))
 def test_version(self): self.assertEqual((ROOT/'07-Manifestes/VERSION').read_text().strip(),'6.88')
if __name__=='__main__': unittest.main()
