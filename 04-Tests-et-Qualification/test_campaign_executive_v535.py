import unittest
from campaign_executive_v535 import executive_summary, decision_register

class ExecutiveTests(unittest.TestCase):
    def report(self):
        return {'events':[{'severity':'critical','count':2,'coverage':'partial'}, {'severity':'warning','count':1,'coverage':'complete'}],
                'groups':[{'severity':'warning','total_count':1,'code':'slow','partial_evidence':False},
                          {'severity':'critical','total_count':2,'code':'route_mismatch','partial_evidence':True}],
                'overall_gate':{'selected_policy':'default'}, 'campaign_count':3,'compared_pairs':2,'severity_filter':'all'}
    def test_priority_order(self):
        self.assertEqual([a['priority'] for a in executive_summary(self.report())['priority_actions']],['P1','P2'])
    def test_counts(self): self.assertEqual(executive_summary(self.report())['counts_by_severity']['critical'],2)
    def test_incomplete(self): self.assertEqual(executive_summary(self.report())['incomplete_evidence_events'],1)
    def test_readonly(self): self.assertFalse(executive_summary(self.report())['production_activation'])
    def test_gate_preserved(self): self.assertEqual(executive_summary(self.report())['global_gate']['selected_policy'],'default')
    def test_register(self):
        r=decision_register(executive_summary(self.report()))
        self.assertTrue(r['template_only']); self.assertEqual(r['entries'][0]['decision'],'UNDECIDED')
    def test_empty(self):
        r=self.report();r['events']=[];r['groups']=[]
        self.assertEqual(executive_summary(r)['priority_actions'][0]['type'],'no_alerts_in_scope')
    def test_bad_event(self):
        r=self.report();r['events'][0]['count']=-1
        with self.assertRaises(ValueError): executive_summary(r)
    def test_bad_group(self):
        r=self.report();r['groups'][0]['total_count']=-1
        with self.assertRaises(ValueError): executive_summary(r)
