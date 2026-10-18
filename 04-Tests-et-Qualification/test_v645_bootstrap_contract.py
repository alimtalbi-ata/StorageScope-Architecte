import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
B=ROOT/'02-Compilation-Windows'
class BootstrapContract(unittest.TestCase):
 def test_version(self):
  self.assertEqual((ROOT/'07-Manifestes/VERSION').read_text().strip(),'6.45')
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
  self.assertIn('6.45',(B/'StorageScope.iss').read_text())
  self.assertIn("VERSION = '6.45'",(ROOT/'03-Sources/storagescope_windows.py').read_text())
if __name__=='__main__': unittest.main()
