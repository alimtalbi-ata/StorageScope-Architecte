import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"03-Sources"))
from governance_desktop import filter_candidates

class SearchOptimization(unittest.TestCase):
 def setUp(self):
  self.rows=[('NETAPP-001',{'asset_ids':['netapp-001'],'review_eligibility':'REVIEW_REQUIRED','note':'Paris site'}),('PURE-002',{'asset_ids':['pure-002'],'review_eligibility':'BLOCKED_CONTRADICTION','note':'Lyon site'})]
 def test_fast_path_no_serialization(self):
  with patch('governance_desktop.json.dumps',side_effect=AssertionError('unnecessary serialization')):
   self.assertEqual([i for i,*_ in filter_candidates(self.rows[:1],'netapp')],[0])
 def test_fallback_serializes_note(self):
  self.assertEqual([i for i,*_ in filter_candidates(self.rows,'paris')],[0])
 def test_multi_term_combined(self):
  self.assertEqual([i for i,*_ in filter_candidates(self.rows,'netapp paris')],[0])
 def test_identity_and_block(self):
  self.assertEqual([i for i,*_ in filter_candidates(self.rows,'status:blocked pure')],[1])
 def test_no_mutation(self):
  import copy
  before=copy.deepcopy(self.rows);filter_candidates(self.rows,'pure');self.assertEqual(self.rows,before)
if __name__=='__main__':unittest.main()
