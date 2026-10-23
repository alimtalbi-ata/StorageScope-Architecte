import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class PortableSmokeContract(unittest.TestCase):
 def test_ci_runs_smoke(self):
  s=(ROOT/'.github/workflows/windows-build.yml').read_text()
  self.assertIn('Run portable Windows smoke test',s)
  self.assertIn('windows-portable-smoke-report.json',s)
 def test_smoke_verifies_executable(self):
  s=(ROOT/'02-Compilation-Windows/qualify-portable-smoke-windows.ps1').read_text()
  for x in ('Expand-Archive','--version-file','--self-test','cleanup','ConvertTo-Json'):
   self.assertIn(x,s)
 def test_staged_smoke_script(self):
  s=(ROOT/'02-Compilation-Windows/build-all-windows.ps1').read_text()
  self.assertIn("'qualify-portable-smoke-windows.ps1'",s)
 def test_version(self):
  release=(ROOT/'07-Manifestes/VERSION').read_text(encoding='utf-8').strip()
  self.assertEqual(release,(ROOT/'03-Sources/VERSION').read_text(encoding='utf-8').strip())
  self.assertGreaterEqual(tuple(map(int,release.split('.'))),(6,93))
if __name__=='__main__':unittest.main()
