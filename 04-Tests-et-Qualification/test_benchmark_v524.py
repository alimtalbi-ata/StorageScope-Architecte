import unittest
from benchmark_analysis_v524 import summarize

def pairs(gains, categories=1):
    result=[]
    for category in range(categories):
        for i,gain in enumerate(gains):
            result.append(dict(id=f'{category}-{i}',nodes=40+category,edits=3,spacing=115,
                               baseline_seconds=.1,candidate_seconds=.1*(1-gain),routes_equal=True))
    return result

class BenchmarkV524Tests(unittest.TestCase):
    def test_category_dispersion(self):
        r=summarize(pairs([.01,.02,.03]))
        self.assertEqual(r['categories'][0]['samples'],3)
        self.assertAlmostEqual(r['categories'][0]['spread'],.02)
    def test_missing_repetitions_blocks(self):
        r=summarize(pairs([.08]*2,categories=8))
        self.assertEqual(r['reason'],'insufficient_category_repetitions')
    def test_category_regression_blocks(self):
        r=summarize(pairs([.09]*12)+[dict(p,id='extra-'+p['id'],nodes=80,candidate_seconds=.101) for p in pairs([.01]*3)])
        self.assertEqual(r['reason'],'category_median_regression')
    def test_invalid_duration_fails_closed(self):
        with self.assertRaises(ValueError): summarize(pairs([.1])+[dict(pairs([.1])[0],id='bad',candidate_seconds=float('nan'))])
    def test_unequal_routes_rejected(self):
        p=pairs([.1,.1,.1]);p[1]['routes_equal']=False
        with self.assertRaises(ValueError): summarize(p)
