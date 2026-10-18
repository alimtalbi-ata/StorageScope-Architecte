import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"03-Sources"))
from governance_desktop import filter_candidates
class TestV658(unittest.TestCase):
 def setUp(self):
  self.items=[("KEY1",{"asset_ids":["netapp-1"],"review_eligibility":"REVIEW_REQUIRED","note":"Paris site"}),("KEY2",{"asset_ids":["pure-2"],"review_eligibility":"BLOCKED_CONTRADICTION","note":"Lyon site"})]
 def test_unqualified_and(self):self.assertEqual([x[0] for x in filter_candidates(self.items,"site Paris")],[0])
 def test_qualified_and(self):self.assertEqual([x[0] for x in filter_candidates(self.items,"asset:netapp key:key1")],[0])
 def test_mixed(self):self.assertEqual([x[0] for x in filter_candidates(self.items,"status:blocked lyon")],[1])
 def test_empty_prefix(self):self.assertEqual(filter_candidates(self.items,"asset:"),[])
 def test_state(self):self.assertEqual([x[0] for x in filter_candidates(self.items,state="BLOCKED_CONTRADICTION")],[1])
if __name__=="__main__":unittest.main()
