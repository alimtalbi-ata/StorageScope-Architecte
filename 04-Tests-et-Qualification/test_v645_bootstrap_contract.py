import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
B=ROOT/'02-Compilation-Windows'
class BootstrapContract(unittest.TestCase):
 def test_version(self):
  v=(ROOT/'07-Manifestes/VERSION').read_text(encoding='utf-8').strip(); self.assertRegex(v,r'^\d+\.\d+$'); self.assertGreaterEqual(tuple(map(int,v.split('.'))),(6,45))
 def test_preflight_allows_bootstrap(self):
  s=(B/'preflight.ps1').read_text()
  self.assertIn('Write-Warning',s)
  self.assertNotIn("throw 'Python introuvable'",s)
 def test_engine_installs_python(self):
  self.assertIn('Python.Python.3.12',(B/'build-engine-windows.ps1').read_text())
 def test_failure_logs_retained(self):
  s=(B/'build-all-windows.ps1').read_text()
  self.assertIn('failed-build-logs',s)
  self.assertIn('diagnostic stage retained',s)
 def test_versions_aligned(self):
  v=(ROOT/'07-Manifestes/VERSION').read_text(encoding='utf-8').strip(); self.assertIn(f'#define AppVersion "{v}"',(B/'StorageScope.iss').read_text(encoding='utf-8'))
  self.assertIn(f"VERSION = '{v}'",(ROOT/'03-Sources/storagescope_windows.py').read_text(encoding='utf-8'))
if __name__=='__main__': unittest.main()
