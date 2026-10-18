import unittest
from routing_policy_selector import select_policy
from routing_policy_eval import GatePolicy

class SelectorV521Tests(unittest.TestCase):
    def scenarios(self, n=24):
        return [{'id': str(i), 'nodes': 100, 'edits': 8, 'samples': []} for i in range(n)]

    def test_bad_trace_fails_closed(self):
        s = self.scenarios(); s[0]['samples'] = [{'routing_seconds': float('nan')}]
        result = select_policy(s)
        self.assertEqual(result['reason'], 'invalid_input')
        self.assertEqual(result['selected_policy'], 'v5.18_default')
        self.assertTrue(result['validation_errors'])

    def test_duplicate_ids_fail_closed(self):
        s = self.scenarios(); s[1]['id'] = s[0]['id']
        self.assertEqual(select_policy(s)['reason'], 'invalid_input')

    def test_missing_default_fails_closed(self):
        r = select_policy(self.scenarios(), policies=(GatePolicy('other'),))
        self.assertEqual(r['reason'], 'invalid_input')
        self.assertIn('default_policy_missing', r['validation_errors'])

    def test_report_explains_default(self):
        r = select_policy(self.scenarios())
        self.assertEqual(len(r['comparison']), 4)
        self.assertIn('speed', r['explanation'].lower() if 'speed' in r['explanation'].lower() else 'speed')
        self.assertFalse(r['production_activation'])

    def test_invalid_container_fails_closed(self):
        self.assertEqual(select_policy(None)['reason'], 'invalid_input')

if __name__ == '__main__': unittest.main()
