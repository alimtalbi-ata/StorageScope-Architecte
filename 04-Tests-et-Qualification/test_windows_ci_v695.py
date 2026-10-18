import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestReleaseGate(unittest.TestCase):
 def setUp(self): self.text=(ROOT/'.github/workflows/windows-build.yml').read_text()
 def test_qualified_only_on_success(self):
  s=self.text.split('name: StorageScope-Windows-QUALIFIED')[0]
  self.assertIn('if: success()',s[-130:])
 def test_diagnostics_always(self):
  s=self.text.split('name: StorageScope-Windows-DIAGNOSTICS')[0]
  self.assertIn('if: always()',s[-130:])
 def test_explicit_final_gate(self):
  self.assertIn("if ($report.status -ne 'PASS')",self.text)
  self.assertIn('verify-binary-delivery.py',self.text)
 def test_no_binary_in_diagnostics(self):
  s=self.text.split('name: StorageScope-Windows-DIAGNOSTICS')[1]
  self.assertNotIn('binary/v*/**',s)
if __name__=='__main__': unittest.main()
