import unittest
from benchmark_stability_v525 import audit_campaigns

def campaign(i,gain=.12):
    return {'id':str(i),'pairs':[{'id':str(j),'nodes':100,'edits':3,'spacing':100,'baseline_seconds':.1,'candidate_seconds':.1*(1-gain),'routes_equal':True} for j in range(12)]}
class StabilityTests(unittest.TestCase):
    def test_insufficient(self): self.assertEqual(audit_campaigns([campaign(1)])['reason'],'insufficient_campaigns')
    def test_stable(self): self.assertEqual(audit_campaigns([campaign(i) for i in range(3)])['selected_policy'],'candidate_measured')
    def test_regression(self): self.assertEqual(audit_campaigns([campaign(1),campaign(2),campaign(3,-.2)])['selected_policy'],'default')
    def test_drift(self): self.assertEqual(audit_campaigns([campaign(1),campaign(2),campaign(3,.3)])['reason'],'cross_campaign_drift_or_missing_category')
    def test_duplicate(self):
        with self.assertRaises(ValueError): audit_campaigns([campaign(1),campaign(1)])
    def test_bad_duration(self):
        c=campaign(1);c['pairs'][0]['baseline_seconds']=float('nan')
        with self.assertRaises(ValueError): audit_campaigns([c])
