import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_desktop import page_summary, display_assets, filter_candidates
class Governance652(unittest.TestCase):
 def test_empty(self): self.assertEqual(page_summary(0,12),'0 résultat · page 1/1')
 def test_first(self): self.assertIn('1–100 sur 251',page_summary(251,0))
 def test_last(self): self.assertIn('201–251 sur 251',page_summary(251,5))
 def test_short_assets(self): self.assertEqual(display_assets({'asset_ids':['a','b']}),'a, b')
 def test_long_assets(self): self.assertEqual(len(display_assets({'asset_ids':['x'*300]})),180)
 def test_scalar_assets(self): self.assertEqual(display_assets({'asset_ids':'abc'}),'abc')
 def test_stable_index(self):
  items=[('a',{'asset_ids':['x']}),('b',{'asset_ids':['y']})]
  self.assertEqual(filter_candidates(items,'asset:y')[0][0],1)
if __name__=='__main__': unittest.main()
