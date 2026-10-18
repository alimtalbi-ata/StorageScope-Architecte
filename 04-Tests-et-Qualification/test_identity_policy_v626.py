import sys,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from identity_policy import analyze
class IdentityTests(unittest.TestCase):
 def setUp(self):
  self.a={'id':'a','source':'s1','vendor':'NetApp','serial':'AB-12','wwn':'50:00:AA','type':'array'}
  self.b={'id':'b','source':'s2','vendor':'netapp','serial':'ab12','wwn':'5000aa','type':'array'}
 def test_match(self): self.assertEqual(analyze([self.a,self.b])['candidates'][0]['status'],'REVIEW_REQUIRED')
 def test_conflicting_wwn(self):
  b={**self.b,'wwn':'other'}; self.assertIn('wwn',analyze([self.a,b])['candidates'][0]['contradictions'])
 def test_vendor(self):
  b={**self.b,'vendor':'Dell'}; self.assertIn('vendor',analyze([self.a,b])['candidates'][0]['contradictions'])
 def test_type(self):
  b={**self.b,'type':'switch'}; self.assertIn('type',analyze([self.a,b])['candidates'][0]['contradictions'])
 def test_no_mutation(self):
  records=[self.a,self.b]; before=copy.deepcopy(records); analyze(records); self.assertEqual(records,before)
 def test_no_automatic_merges(self): self.assertEqual(analyze([self.a,self.b])['automatic_merges'],0)
 def test_invalid(self): self.assertEqual(len(analyze([None])['invalid_records']),1)
 def test_empty(self): self.assertEqual(analyze([])['candidates'],[])
 def test_bad_input(self):
  with self.assertRaises(ValueError): analyze({})
 def test_no_false_positive(self): self.assertEqual(analyze([self.a,{**self.b,'serial':'other','wwn':'other'}])['candidates'],[])
if __name__=='__main__': unittest.main()
