import unittest
from unittest.mock import patch
from campaign_kpi_v531 import comparison_kpis, evidence_for_point

class KPI531Tests(unittest.TestCase):
    def setUp(self):
        self.data={'first_sha256':'a'*64,'second_sha256':'b'*64,
            'summary':{'delta_median_gain':-.02,'second_mismatches':1,'second_regressions':2},
            'matched_count':3,'unmatched_count':1,'overall_gate':{'selected_policy':'default'},
            'points':[{'id':'a','delta':.1,'first_evidence':{'gain':.1},'second_evidence':{'gain':.2}},
                      {'id':'b','delta':-.2,'first_evidence':{},'second_evidence':{}},
                      {'id':'c','delta':0,'first_evidence':{},'second_evidence':{}},
                      {'id':'d','delta':None,'first_evidence':None,'second_evidence':{}}]}
    def get(self):
        with patch('campaign_kpi_v531.overlay_data',return_value=self.data):
            return comparison_kpis(None,'A','B',nodes=40)
    def test_counts(self):
        k=self.get();self.assertEqual((k['improved'],k['degraded'],k['unchanged'],k['unmatched']),(1,1,1,1))
    def test_alerts(self):
        self.assertEqual([a['code'] for a in self.get()['alerts']],['route_mismatch','sample_regression','paired_degradation','unmatched_evidence'])
    def test_gate_unchanged(self):
        k=self.get();self.assertEqual(k['overall_gate'],self.data['overall_gate']);self.assertFalse(k['production_activation'])
    def test_evidence(self):
        self.assertEqual(evidence_for_point(self.get(),'a')['first']['gain'],.1)
    def test_missing(self):
        with self.assertRaises(ValueError): evidence_for_point(self.get(),'missing')
    def test_empty_id(self):
        with self.assertRaises(ValueError): evidence_for_point(self.get(),'')
    def test_no_alerts(self):
        self.data['summary'].update(second_mismatches=0,second_regressions=0)
        self.data['points']=[{'id':'a','delta':.1,'first_evidence':{},'second_evidence':{}}]
        self.data['matched_count']=1;self.data['unmatched_count']=0
        self.assertEqual(self.get()['alerts'],[])
    def test_digest_provenance(self):
        self.assertEqual(evidence_for_point(self.get(),'a')['campaign_sha256'],('a'*64,'b'*64))
if __name__=='__main__':unittest.main()
