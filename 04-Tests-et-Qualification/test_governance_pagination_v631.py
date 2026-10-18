import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_desktop import eligible_candidates,filter_candidates,paginate_candidates,can_decide
class TestGovernanceV631(unittest.TestCase):
 def test_blocked_visible(self):
  report={'reconciliation':{'candidates':[{'review_eligibility':'BLOCKED_CONTRADICTION','asset_ids':['a','b']}]}}
  rows=eligible_candidates(report)
  self.assertEqual(len(rows),1)
  self.assertFalse(can_decide(rows[0][1]))
 def test_blocked_search(self):
  rows=[('BLOCKED:0',{'review_eligibility':'BLOCKED_CONTRADICTION','asset_ids':['Pure']})]
  self.assertEqual(len(filter_candidates(rows,'pure','BLOCKED_CONTRADICTION')),1)
 def test_pages(self):
  rows=list(range(251))
  self.assertEqual(len(paginate_candidates(rows,0)),100)
  self.assertEqual(paginate_candidates(rows,2)[-1],250)
  self.assertEqual(paginate_candidates(rows,3),[])
 def test_invalid_page(self):
  with self.assertRaises(ValueError):paginate_candidates([],0,0)
 def test_no_approval_without_key(self):
  self.assertFalse(can_decide({'review_eligibility':'REVIEW_REQUIRED'}))
if __name__=='__main__':unittest.main()
