import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_desktop import filter_candidates, paginate_candidates
class TestV657(unittest.TestCase):
 def setUp(self):
  self.rows=[('key-1',{'asset_ids':['netapp-1'],'review_eligibility':'REVIEW_REQUIRED','notes':'alpha'}),('key-2',{'asset_ids':['pure-2'],'review_eligibility':'BLOCKED_CONTRADICTION','notes':'beta'})]
 def test_empty_query_stable_indices(self):self.assertEqual([r[0] for r in filter_candidates(self.rows)],[0,1])
 def test_status_without_serialization(self):self.assertEqual([r[0] for r in filter_candidates(self.rows,'', 'BLOCKED_CONTRADICTION')],[1])
 def test_field_only_query(self):self.assertEqual([r[0] for r in filter_candidates(self.rows,'asset:netapp')],[0])
 def test_free_text(self):self.assertEqual([r[0] for r in filter_candidates(self.rows,'beta')],[1])
 def test_pagination(self):self.assertEqual([r[0] for r in paginate_candidates(filter_candidates(self.rows),1,1)],[1])
if __name__=='__main__':unittest.main()
