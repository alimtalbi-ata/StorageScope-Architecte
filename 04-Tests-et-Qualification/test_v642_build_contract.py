import pathlib, re, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
B = ROOT / "02-Compilation-Windows"
class BuildContract(unittest.TestCase):
 def test_version(self):
  v=(ROOT/"07-Manifestes/VERSION").read_text(encoding="utf-8").strip(); self.assertRegex(v,r"^\d+\.\d+$"); self.assertGreaterEqual(tuple(map(int,v.split("."))),(6,42)); self.assertIn(f'#define AppVersion "{v}"',(B/"StorageScope.iss").read_text(encoding="utf-8"))
 def test_manifest_paths_interpolated(self):
  s=(B / "build-engine-windows.ps1").read_text()
  self.assertNotIn("'installer\\release-manifest-v${releaseVersion}.json'", s)
  self.assertIn('("installer\\release-manifest-v{0}.json" -f $releaseVersion)', s)
 def test_portable_manifest_interpolated(self):
  s=(B / "build-engine-windows.ps1").read_text()
  self.assertIn('("portable-manifest-v{0}.json" -f $releaseVersion)', s)
 def test_qualification_hash_verification(self):
  s=(B / "qualify-native-windows.ps1").read_text()
  self.assertIn("Get-FileHash", s)
  self.assertIn("Release manifest version mismatch", s)
if __name__ == "__main__": unittest.main()
