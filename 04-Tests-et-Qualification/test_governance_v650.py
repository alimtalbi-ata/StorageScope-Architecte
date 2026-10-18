import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_desktop import page_bounds,filter_candidates,eligible_candidates,can_decide
class TestV650(unittest.TestCase):
 def test_empty(self): self.assertEqual(page_bounds(0,15),(0,0))
 def test_clamp_after_filter(self): self.assertEqual(page_bounds(3,9),(0,0))
 def test_last_page(self): self.assertEqual(page_bounds(201,7),(2,2))
 def test_negative_page(self): self.assertEqual(page_bounds(250,-5),(0,2))
 def test_invalid_total(self):
  with self.assertRaises(ValueError): page_bounds(-1,0)
 def test_blocked_cannot_decide(self):
  rows=eligible_candidates({'reconciliation':{'candidates':[{'review_eligibility':'BLOCKED_CONTRADICTION'}]}})
  self.assertFalse(can_decide(rows[0][1]))
 def test_filter_stable_indices(self):
  rows=[('k0',{'asset_ids':['x']}),('k1',{'asset_ids':['y']})]
  self.assertEqual(filter_candidates(rows,'y')[0][0],1)
if __name__=='__main__':unittest.main()
