import unittest
from routing_policy_performance import evaluate_performance

class PerformanceGateV522Tests(unittest.TestCase):
    def pairs(self, n=12, baseline=1., candidate=.8):
        return [dict(id=str(i), baseline_seconds=baseline, candidate_seconds=candidate, routes_equal=True) for i in range(n)]
    def test_measured_gain(self):
        self.assertEqual(evaluate_performance(self.pairs())['reason'], 'measured_candidate_preferred')
    def test_regression_blocks_even_with_good_median(self):
        p=self.pairs(); p[0]['candidate_seconds']=1.3
        self.assertEqual(evaluate_performance(p)['reason'], 'regression_guard')
    def test_mismatch_blocks(self):
        p=self.pairs(); p[2]['routes_equal']=False
        self.assertEqual(evaluate_performance(p)['reason'], 'route_mismatch_or_unverified')
    def test_missing_or_nan_blocks(self):
        p=self.pairs(); p[0]['candidate_seconds']=float('nan')
        self.assertEqual(evaluate_performance(p)['reason'], 'invalid_input')
    def test_insufficient_pairs(self):
        self.assertEqual(evaluate_performance(self.pairs(4))['reason'], 'insufficient_paired_measurements')
    def test_no_gain(self):
        self.assertEqual(evaluate_performance(self.pairs(candidate=.99))['reason'], 'gain_below_threshold')
    def test_duplicate_ids(self):
        p=self.pairs(); p[1]['id']='0'
        self.assertEqual(evaluate_performance(p)['reason'], 'invalid_input')
