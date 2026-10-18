import pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
S=(ROOT/'02-Compilation-Windows/qualify-native-windows.ps1').read_text()
class QualificationContract(unittest.TestCase):
 def test_version(self): self.assertEqual((ROOT/'07-Manifestes/VERSION').read_text().strip(),'6.43')
 def test_skip_installer_skips_manifest(self): self.assertIn("if (-not $SkipInstaller) { Check 'release_manifest'",S)
 def test_hash_check(self): self.assertIn('Artifact hash mismatch',S)
 def test_missing_exe_fails(self): self.assertIn('EXE not built',S)
 def test_nonwindows_guard(self): self.assertIn('Native qualification requires Windows',S)
 def test_report_fails_closed(self): self.assertIn("if ($report.overall -ne 'PASS') { exit 1 }",S)
if __name__=='__main__': unittest.main()
