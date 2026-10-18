import json
import tempfile
import unittest
from pathlib import Path
from campaign_history_v526 import CampaignHistory
from campaign_dashboard_v527 import dashboard_data, export_dashboard


def campaign(i, gain=.12):
    return {'id':str(i),'pairs':[{'id':str(j),'nodes':100,'edits':3,'spacing':100,
       'baseline_seconds':.1,'candidate_seconds':.1*(1-gain),'routes_equal':True} for j in range(12)]}

class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.db=CampaignHistory(Path(self.tmp.name)/'db.sqlite')
    def test_empty(self):
        self.assertEqual(dashboard_data(self.db)['displayed_count'],0)
    def test_series(self):
        for i in range(3): self.db.add(campaign(i))
        d=dashboard_data(self.db)
        self.assertEqual(d['displayed_count'],3)
        self.assertAlmostEqual(d['campaigns'][0]['median_gain'],.12)
    def test_filter(self):
        self.db.add(campaign(1))
        self.assertEqual(dashboard_data(self.db,nodes=200)['displayed_count'],0)
        self.assertEqual(dashboard_data(self.db,edits=3)['displayed_count'],1)
    def test_invalid_filter(self):
        with self.assertRaises(ValueError):dashboard_data(self.db,nodes=True)
        with self.assertRaises(ValueError):dashboard_data(self.db,edits=-1)
    def test_global_gate_not_affected_by_filter(self):
        for i in range(3):self.db.add(campaign(i))
        a=dashboard_data(self.db)
        b=dashboard_data(self.db,nodes=999)
        self.assertEqual(a['overall_gate'],b['overall_gate'])
        self.assertTrue(b['filter_is_descriptive_only'])
    def test_regression_visible(self):
        self.db.add(campaign(1,-.20))
        self.assertEqual(dashboard_data(self.db)['campaigns'][0]['regressions'],12)
    def test_export(self):
        self.db.add(campaign(1)); path=Path(self.tmp.name)/'export.json'
        export_dashboard(self.db,path)
        self.assertEqual(json.loads(path.read_text())['displayed_count'],1)
    def test_no_activation(self):
        self.db.add(campaign(1))
        self.assertFalse(dashboard_data(self.db)['production_activation'])
if __name__=='__main__': unittest.main()
