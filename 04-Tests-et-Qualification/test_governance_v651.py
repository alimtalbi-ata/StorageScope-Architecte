import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"03-Sources"))
from governance_desktop import filter_candidates,parse_search
ROWS=[("asset:01",{"asset_ids":["netapp-01"],"review_eligibility":"REVIEW_REQUIRED","site":"Paris"}),
      ("asset:02",{"asset_ids":["pure-02"],"review_eligibility":"BLOCKED_CONTRADICTION","site":"Lyon"}),
      ("asset:03",{"asset_ids":None,"review_eligibility":"REVIEW_REQUIRED","site":"Paris"})]
class SearchV651(unittest.TestCase):
 def test_multi_term_and(self): self.assertEqual([x[0] for x in filter_candidates(ROWS,"Paris netapp")],[0])
 def test_asset_prefix(self): self.assertEqual([x[0] for x in filter_candidates(ROWS,"asset:pure")],[1])
 def test_status_prefix(self): self.assertEqual([x[0] for x in filter_candidates(ROWS,"status:blocked")],[1])
 def test_key_prefix(self): self.assertEqual([x[0] for x in filter_candidates(ROWS,"key:02")],[1])
 def test_phrase(self): self.assertEqual(parse_search('"site paris" asset:01'),['site paris','asset:01'])
 def test_null_assets(self): self.assertEqual([x[0] for x in filter_candidates(ROWS,"Paris")],[0,2])
 def test_stable_index(self): self.assertEqual(filter_candidates(ROWS,"Lyon")[0][0],1)
 def test_no_mutation(self):
  import copy
  original=copy.deepcopy(ROWS);filter_candidates(ROWS,"asset:netapp");self.assertEqual(ROWS,original)
if __name__=="__main__":unittest.main()
