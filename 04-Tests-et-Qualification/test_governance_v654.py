import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_desktop import explain_candidate
class ExplainCandidateTests(unittest.TestCase):
 def test_blocked_not_actionable(self):
  x=explain_candidate({'review_eligibility':'BLOCKED_CONTRADICTION','review_key':'abc','asset_ids':['a','b']})
  self.assertFalse(x['decision_allowed']); self.assertIn('interdite',x['reason'])
 def test_evidence_preserved(self):
  x=explain_candidate({'identity_evidence':['serial','wwn'],'asset_ids':['n1']})
  self.assertEqual(x['identity_evidence'],['serial','wwn'])
 def test_conflicts_explicit_only(self):
  x=explain_candidate({'contradictions':['serial mismatch']})
  self.assertEqual(x['conflicts']['contradictions'],['serial mismatch'])
 def test_no_fabricated_confidence(self):
  x=explain_candidate({'asset_ids':['a']})
  self.assertNotIn('confidence',x)
 def test_invalid_candidate(self):
  with self.assertRaises(TypeError): explain_candidate(None)
if __name__=='__main__': unittest.main()
