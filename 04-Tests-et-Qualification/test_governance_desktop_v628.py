import sys, unittest, tempfile, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_desktop import load_assessment,eligible_candidates
class DesktopTests(unittest.TestCase):
 def test_reject_non_array(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.json';p.write_text('{}')
   with self.assertRaises(ValueError):load_assessment(p)
 def test_missing_file(self):
  with self.assertRaises(FileNotFoundError):load_assessment('/does/not/exist.json')
 def test_blocked_hidden(self):
  report={'reconciliation':{'candidates':[{'review_eligibility':'BLOCKED_CONTRADICTION','review_key':'x','asset_ids':['a','b']}]}}
  self.assertEqual(eligible_candidates(report),[])
 def test_ambiguous_hidden(self):
  report={'reconciliation':{'candidates':[{'review_key':'x','asset_ids':['a']}]}}
  self.assertEqual(eligible_candidates(report),[])
if __name__=='__main__':unittest.main()
