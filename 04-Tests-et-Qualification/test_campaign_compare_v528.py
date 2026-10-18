import json
import tempfile
import unittest
from pathlib import Path
from campaign_history_v526 import CampaignHistory
from campaign_compare_v528 import compare_campaigns, export_comparison


def campaign(cid, gain, nodes=100):
    return {'id': cid, 'pairs': [{'id': str(i), 'nodes': nodes, 'edits': 3, 'spacing': 100,
        'baseline_seconds': 1., 'candidate_seconds': 1.-gain, 'routes_equal': True} for i in range(12)]}

class CompareV528Tests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.dir=Path(t.name); self.history=CampaignHistory(self.dir/'history.sqlite')
        self.history.add(campaign('a', .1)); self.history.add(campaign('b', .2))
    def test_delta(self):
        self.assertAlmostEqual(compare_campaigns(self.history,'a','b')['delta_median_gain'], .1)
    def test_evidence(self):
        self.assertEqual(len(compare_campaigns(self.history,'a','b')['campaigns'][0]['evidence']),12)
    def test_missing(self):
        with self.assertRaises(ValueError): compare_campaigns(self.history,'a','absent')
    def test_same(self):
        with self.assertRaises(ValueError): compare_campaigns(self.history,'a','a')
    def test_empty_filter(self):
        d=compare_campaigns(self.history,'a','b',nodes=999)
        self.assertIsNone(d['delta_median_gain'])
    def test_filter_does_not_change_gate(self):
        a=compare_campaigns(self.history,'a','b'); b=compare_campaigns(self.history,'a','b',nodes=999)
        self.assertEqual(a['overall_gate'], b['overall_gate'])
    def test_export(self):
        path=self.dir/'comparison.json'; export_comparison(self.history,'a','b',path)
        self.assertEqual(json.loads(path.read_text())['campaigns'][0]['id'],'a')
    def test_read_only(self):
        d=compare_campaigns(self.history,'a','b'); self.assertFalse(d['production_activation'])
        self.assertTrue(d['recommendation_only'])
