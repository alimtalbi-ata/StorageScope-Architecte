import unittest
from routing_policy_eval import GatePolicy, should_full_route, compare_policies, DEFAULT_POLICIES

class PolicyComparisonTests(unittest.TestCase):
    def test_default_policy_matches_hard_limit(self):
        p = DEFAULT_POLICIES[0]
        self.assertEqual(should_full_route(p, 8, 300, []), (True, 'hard_limit'))
        self.assertFalse(should_full_route(p, 7, 300, [])[0])

    def test_measured_cost_requires_actual_zero_reuse(self):
        p = GatePolicy('custom', hard_limit=20, min_edits=4, ratio=.05)
        samples = [dict(validation_seconds=.03, routing_seconds=.01, reused=0) for _ in range(3)]
        self.assertEqual(should_full_route(p, 6, 100, samples), (True, 'measured_cost'))
        samples[-1]['reused'] = 1
        self.assertFalse(should_full_route(p, 6, 100, samples)[0])

    def test_comparison_does_not_mutate_traces(self):
        cases = [{'id': 'a', 'nodes': 100, 'edits': 8, 'samples': []}, {'id': 'b', 'nodes': 100, 'edits': 1, 'samples': []}]
        before = repr(cases)
        results = compare_policies(cases, DEFAULT_POLICIES)
        self.assertEqual(repr(cases), before)
        self.assertEqual(len(results), 4)
        self.assertEqual(results[0]['full_routes'], 1)
        self.assertEqual(results[0]['partial_eligible'], 1)

    def test_invalid_policy_rejected(self):
        with self.assertRaises(ValueError): GatePolicy('bad', hard_limit=0)
