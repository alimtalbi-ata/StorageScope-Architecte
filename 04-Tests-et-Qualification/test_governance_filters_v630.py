import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"03-Sources"))
from governance_desktop import filter_candidates
class Filters(unittest.TestCase):
 def setUp(self):self.data=[("keyA",{"asset_ids":["NetApp-1"],"review_eligibility":"REVIEW_REQUIRED"}),("keyB",{"asset_ids":["Pure-2"],"review_eligibility":"BLOCKED_CONTRADICTION"})]
 def test_all(self):self.assertEqual(len(filter_candidates(self.data)),2)
 def test_casefold(self):self.assertEqual(filter_candidates(self.data,"netapp")[0][0],0)
 def test_status(self):self.assertEqual(len(filter_candidates(self.data,state="BLOCKED_CONTRADICTION")),1)
 def test_combined(self):self.assertEqual(filter_candidates(self.data,"pure","REVIEW_REQUIRED"),[])
 def test_unchanged(self):filter_candidates(self.data,"x");self.assertEqual(len(self.data),2)
if __name__=="__main__":unittest.main()
