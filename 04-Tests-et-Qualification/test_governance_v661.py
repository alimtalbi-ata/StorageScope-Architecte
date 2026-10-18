import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"03-Sources"))
from governance_desktop import filter_candidates
class TestV661(unittest.TestCase):
 def setUp(self):
  self.items=[("K-01",{"asset_ids":["netapp-01"],"note":"site 4 fabric 12","review_eligibility":"BLOCKED_CONTRADICTION"}),("K-02",{"asset_ids":["pure-02"],"note":"site 5","review_eligibility":"REVIEW_REQUIRED"})]
 def test_free_text_note(self): self.assertEqual([x[0] for x in filter_candidates(self.items,"site 4")],[0])
 def test_key_search(self): self.assertEqual([x[0] for x in filter_candidates(self.items,"key:k-02")],[1])
 def test_status_and_asset(self): self.assertEqual([x[0] for x in filter_candidates(self.items,"status:blocked asset:netapp")],[0])
 def test_stable_index(self): self.assertEqual(filter_candidates(self.items,"pure")[0][0],1)
 def test_empty(self): self.assertEqual(len(filter_candidates(self.items)),2)
if __name__=="__main__": unittest.main()
