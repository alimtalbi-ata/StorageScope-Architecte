import unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class WindowsCIContract(unittest.TestCase):
 def test_version(self): self.assertEqual((R/'07-Manifestes/VERSION').read_text().strip(),'6.96')
 def test_early_gate(self):
  w=(R/'.github/workflows/windows-build.yml').read_text()
  self.assertLess(w.index('Check release sources and binary workspace'),w.index('Build Windows release'))
  self.assertIn('Already published release in source tree',w)
 def test_source_definitions(self):
  w=(R/'.github/workflows/windows-build.yml').read_text()
  self.assertIn('StorageScope.iss',w);self.assertIn('StorageScope.spec',w)
 def test_qualified_upload_gate(self):
  w=(R/'.github/workflows/windows-build.yml').read_text()
  self.assertIn('Gate release artifacts on complete qualification',w)
  self.assertIn('StorageScope-Windows-QUALIFIED',w)
if __name__=='__main__':unittest.main()
