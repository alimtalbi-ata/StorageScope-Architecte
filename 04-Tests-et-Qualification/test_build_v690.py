import unittest
from pathlib import Path
S=(Path(__file__).resolve().parents[1]/'02-Compilation-Windows/build-all-windows.ps1').read_text()
class BuildGuardTests(unittest.TestCase):
 def test_existing_pending_rejected(self): self.assertIn('Publication precedente non resolue',S)
 def test_pending_preserved(self): self.assertNotIn('Remove-Item -LiteralPath $publishRoot -Recurse -Force',S)
 def test_stage_preserved(self): self.assertIn('Ancien repertoire de compilation a examiner',S)
 def test_binary_preflight(self): self.assertIn('Version deja publiee: $binaryTarget',S)
 def test_binary_stage_preflight(self): self.assertIn('Publication binary non resolue',S)
if __name__=='__main__': unittest.main()
