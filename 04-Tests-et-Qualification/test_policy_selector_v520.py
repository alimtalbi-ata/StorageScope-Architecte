import unittest
from routing_policy_eval import GatePolicy, DEFAULT_POLICIES
from routing_policy_selector import select_policy

class SelectorV520Tests(unittest.TestCase):
    def test_small_sample_fails_closed(self):
        result = select_policy([{'id': 'x', 'nodes': 10, 'edits': 1, 'samples': []}])
        self.assertEqual(result['selected_policy'], 'v5.18_default')
        self.assertEqual(result['reason'], 'insufficient_scenarios')
        self.assertTrue(result['recommendation_only'])

    def test_tie_keeps_default(self):
        scenarios = [{'id': str(i), 'nodes': 100, 'edits': 1, 'samples': []} for i in range(24)]
        result = select_policy(scenarios)
        self.assertEqual(result['selected_policy'], 'v5.18_default')
        self.assertEqual(result['reason'], 'no_strict_improvement')

    def test_selector_is_deterministic(self):
        scenarios = [{'id': str(i), 'nodes': 100, 'edits': 8, 'samples': []} for i in range(30)]
        self.assertEqual(select_policy(scenarios), select_policy(scenarios))

    def test_no_production_activation_contract(self):
        scenarios = [{'id': str(i), 'nodes': 100, 'edits': 1, 'samples': []} for i in range(24)]
        self.assertIs(select_policy(scenarios)['recommendation_only'], True)

if __name__ == '__main__': unittest.main()
