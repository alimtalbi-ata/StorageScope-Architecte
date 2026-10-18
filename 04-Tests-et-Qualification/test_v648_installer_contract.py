import unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class InstallerContract(unittest.TestCase):
 def test_smoke_present(self): self.assertTrue((R/'02-Compilation-Windows/qualify-installer-smoke-windows.ps1').exists())
 def test_smoke_uninstalls(self): self.assertIn('unins000.exe',(R/'02-Compilation-Windows/qualify-installer-smoke-windows.ps1').read_text())
 def test_ci_executes_smoke(self): self.assertIn('qualify-installer-smoke-windows.ps1',(R/'.github/workflows/windows-build.yml').read_text())
 def test_qualification_candidate_pipeline_fixed(self): self.assertIn('$candidates = @(', (R/'02-Compilation-Windows/qualify-native-windows.ps1').read_text())
 def test_versions(self): self.assertEqual((R/'07-Manifestes/VERSION').read_text().strip(),'6.48')
