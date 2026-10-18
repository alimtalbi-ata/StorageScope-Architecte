import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"03-Sources"))
from governance_desktop import filter_candidates,paginate_candidates,page_bounds
class PaginationRegression(unittest.TestCase):
 def test_navigation_reuses_filter(self):
  source=(Path(__file__).resolve().parents[1]/"03-Sources/governance_desktop.py").read_text()
  segment=source.split("    def change_page(delta):",1)[1].split("    ttk.Button(pager",1)[0]
  self.assertIn("refresh(refilter=False)",segment)
 def test_stable_indices(self):
  rows=[(f"K-{i}",{"asset_ids":[f"a-{i}"],"review_eligibility":"REVIEW_REQUIRED"}) for i in range(250)]
  matched=filter_candidates(rows,"status:review_required")
  self.assertEqual([i for i,*_ in paginate_candidates(matched,2,100)],list(range(200,250)))
 def test_page_clamp(self):
  self.assertEqual(page_bounds(12,99),(0,0))
 def test_no_mutation(self):
  rows=[("a",{"asset_ids":["x"]})]
  filter_candidates(rows,"x");self.assertEqual(rows,[('a',{'asset_ids':['x']})])
if __name__=="__main__":unittest.main()
