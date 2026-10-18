import ast, pathlib, tempfile, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class VersionProbeTests(unittest.TestCase):
 def test_version_file_branch_exists(self):
  p=(ROOT/'03-Sources/storagescope_windows.py').read_text()
  self.assertIn("args[0] == '--version-file'",p)
  ast.parse(p)
 def test_gui_build_uses_file_probe(self):
  s=(ROOT/'02-Compilation-Windows/build-engine-windows.ps1').read_text()
  self.assertIn("@('--version-file', $versionProbe)",s)
  self.assertNotIn('(& "$PSScriptRoot\\dist\\StorageScope.exe" --version | Out-String)',s)
 def test_qualifier_uses_file_probe(self):
  s=(ROOT/'02-Compilation-Windows/qualify-native-windows.ps1').read_text()
  self.assertIn('--version-file $probe',s)
 def test_ci_workflow_in_repo_root(self):
  self.assertTrue((ROOT/'.github/workflows/windows-build.yml').is_file())
 def test_versions(self):
  self.assertEqual((ROOT/'07-Manifestes/VERSION').read_text().strip(),'6.46')
if __name__=='__main__': unittest.main()
