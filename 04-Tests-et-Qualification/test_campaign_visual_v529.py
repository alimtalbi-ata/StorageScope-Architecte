import tempfile
import unittest
from pathlib import Path
from campaign_history_v526 import CampaignHistory
from campaign_visual_v529 import overlay_data, draw_overlay
from test_campaign_compare_v528 import campaign

class VisualV529Tests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.h=CampaignHistory(Path(t.name)/'history.sqlite')
        self.h.add(campaign('a',.1));self.h.add(campaign('b',.2))
    def test_matched(self):
        self.assertEqual(overlay_data(self.h,'a','b')['matched_count'],12)
    def test_delta(self):
        self.assertAlmostEqual(overlay_data(self.h,'a','b')['points'][0]['delta'],.1)
    def test_provenance(self):
        self.assertEqual(len(overlay_data(self.h,'a','b')['first_sha256']),64)
    def test_no_filter_data(self):
        self.assertEqual(overlay_data(self.h,'a','b',nodes=999)['points'],[])
    def test_global_gate_unchanged(self):
        self.assertEqual(overlay_data(self.h,'a','b')['overall_gate'],overlay_data(self.h,'a','b',nodes=999)['overall_gate'])
    def test_no_activation(self):
        self.assertFalse(overlay_data(self.h,'a','b')['production_activation'])
    def test_missing_campaign(self):
        with self.assertRaises(ValueError): overlay_data(self.h,'a','missing')
    def test_canvas_empty(self):
        class Canvas:
            def __init__(self):self.calls=[]
            def delete(self,*args):self.calls.append('delete')
            def create_text(self,*args,**kwargs):self.calls.append('text')
        c=Canvas();draw_overlay(c,{'points':[]});self.assertEqual(c.calls,['delete','text'])
