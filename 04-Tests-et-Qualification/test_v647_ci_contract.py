from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class CIContract(unittest.TestCase):
 def test_workflow_fallback(self):
  s=(ROOT/'02-Compilation-Windows/build-all-windows.ps1').read_text()
  self.assertIn("$workflowSource = Join-Path $root '.github/workflows/windows-build.yml'",s)
  self.assertIn('Windows CI workflow missing',s)
 def test_no_stale_native_exit_code(self):
  s=(ROOT/'02-Compilation-Windows/build-all-windows.ps1').read_text()
  self.assertNotIn('Build engine exit code: $LASTEXITCODE',s)
 def test_ci_requires_evidence(self):
  s=(ROOT/'.github/workflows/windows-build.yml').read_text()
  self.assertIn('Qualification evidence missing',s)
 def test_release_version(self):
  v=(ROOT/'07-Manifestes/VERSION').read_text().strip()
  self.assertRegex(v,r'^\d+\.\d+$'); self.assertGreaterEqual(tuple(map(int,v.split('.'))),(6,47))
  self.assertIn(f'#define AppVersion "{v}"',(ROOT/'02-Compilation-Windows/StorageScope.iss').read_text(encoding='utf-8'))
