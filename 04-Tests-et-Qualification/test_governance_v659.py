import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from benchmark_governance_compare_v659 import dataset,run
class TestBenchmark(unittest.TestCase):
 def test_size(self):self.assertEqual(len(dataset(13)),13)
 def test_reproducible(self):self.assertEqual(dataset(10),dataset(10))
 def test_status_mix(self):self.assertEqual(sum(c["review_eligibility"]=="BLOCKED_CONTRADICTION" for _,c in dataset(15)),3)
 def test_comparison(self):
  p=Path(__file__).resolve().parents[1]/"03-Sources/governance_desktop.py"
  r=run(p,p,size=100,repeats=1)
  self.assertEqual(len(r["results"]),5)
  self.assertTrue(all(x["previous"]["matches"]==x["current"]["matches"] for x in r["results"]))
if __name__=="__main__":unittest.main()
