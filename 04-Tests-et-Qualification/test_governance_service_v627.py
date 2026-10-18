import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"03-Sources"))
from governance_service import assess
class TestGovernanceService(unittest.TestCase):
 def test_invalid(self):
  with self.assertRaises(ValueError): assess({})
 def test_empty(self):
  r=assess([]);self.assertEqual(r["automatic_merges"],0);self.assertEqual(r["review_eligible"],0)
 def test_no_mutation(self):
  a=[{"id":"a","source":"x","serial":"123","vendor":"Dell"},{"id":"b","source":"y","serial":"123","vendor":"NetApp"}]
  original=[dict(x) for x in a];r=assess(a);self.assertEqual(a,original);self.assertTrue(r["identity_policy"]["candidates"][0]["status"]=="BLOCKED_CONTRADICTION")
 def test_same_vendor(self):
  a=[{"id":"a","source":"x","serial":"123","vendor":"Dell"},{"id":"b","source":"y","serial":"123","vendor":"Dell"}]
  self.assertEqual(assess(a)["identity_policy"]["candidates"][0]["status"],"REVIEW_REQUIRED")
if __name__=="__main__": unittest.main()
