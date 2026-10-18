import sys, unittest, tempfile, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_desktop import load_assessment,eligible_candidates,can_decide
class DesktopTests(unittest.TestCase):
 def test_reject_non_array(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.json';p.write_text('{}')
   with self.assertRaises(ValueError):load_assessment(p)
 def test_missing_file(self):
  with self.assertRaises(FileNotFoundError):load_assessment('/does/not/exist.json')
 def test_blocked_visible_but_not_actionable(self):
  report={'reconciliation':{'candidates':[{'review_eligibility':'BLOCKED_CONTRADICTION','review_key':'x','asset_ids':['a','b']}]}}
  rows=eligible_candidates(report)
  self.assertEqual(len(rows),1)
  self.assertFalse(can_decide(rows[0][1]))
 def test_ambiguous_visible_but_not_actionable(self):
  report={'reconciliation':{'candidates':[{'review_key':'x','asset_ids':['a']}]}}
  rows=eligible_candidates(report)
  self.assertEqual(len(rows),1)
  self.assertFalse(can_decide(rows[0][1]))
if __name__=='__main__':unittest.main()
