import unittest
from unittest.mock import patch
from campaign_alerts_v532 import alert_view, alert_evidence

class AlertTests(unittest.TestCase):
    def setUp(self):
        self.k={'alerts':[{'severity':'critical','code':'route_mismatch','count':1},
                          {'severity':'warning','code':'paired_degradation','count':1},
                          {'severity':'info','code':'unmatched_evidence','count':1}],
                'points':[{'id':'bad','delta':-.2,'second_evidence':{'routes_equal':False},'first_evidence':{}},
                          {'id':'missing','delta':None,'second_evidence':None,'first_evidence':{}}],
                'overall_gate':{'selected_policy':'default'},'sha256':('a'*64,'b'*64)}
    def view(self,sev='all'):
        with patch('campaign_alerts_v532.comparison_kpis',return_value=self.k):
            return alert_view(None,'a','b',severity=sev)
    def test_all(self): self.assertEqual(len(self.view()['alerts']),3)
    def test_critical(self): self.assertEqual([a['code'] for a in self.view('critical')['alerts']],['route_mismatch'])
    def test_warning(self): self.assertEqual(self.view('warning')['alerts'][0]['evidence_ids'],['bad'])
    def test_info(self): self.assertEqual(self.view('info')['alerts'][0]['evidence_ids'],['missing'])
    def test_invalid(self):
        with self.assertRaises(ValueError): self.view('emergency')
    def test_gate_immutable(self):
        v=self.view('info');self.assertEqual(v['overall_gate'],self.k['overall_gate']);self.assertFalse(v['production_activation'])
    def test_drilldown(self): self.assertEqual(alert_evidence(self.view(),'route_mismatch','bad')['id'],'bad')
    def test_unlinked(self):
        with self.assertRaises(ValueError): alert_evidence(self.view(),'route_mismatch','missing')
