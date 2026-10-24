import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from campaign_timeline_v533 import timeline, export_timeline

class FakeHistory:
    def list(self, limit):
        return [{'id': x, 'recorded_at': '2026-10-16T12:00:00Z', 'sha256': x*64} for x in 'abc']
    def report(self, limit): return {'selected_policy': 'default', 'reason':'test'}

class TimelineTests(unittest.TestCase):
    def setUp(self): self.history=FakeHistory()
    def mocked(self, **kwargs):
        def view(h, a, b, **kw):
            return {'alerts':[{'severity':'warning','code':'paired_degradation','count':2,'evidence_ids':['measure-1'],'evidence_coverage':'partial'}] if kw['severity'] in ('all','warning') else []}
        with patch('campaign_timeline_v533.alert_view', side_effect=view):
            return timeline(self.history, **kwargs)
    def test_pairs(self): self.assertEqual(self.mocked()['compared_pairs'],2)
    def test_group(self): self.assertEqual(self.mocked()['groups'][0]['total_count'],4)
    def test_partial(self): self.assertTrue(self.mocked()['groups'][0]['partial_evidence'])
    def test_severity(self): self.assertEqual(self.mocked(severity='critical')['events'],[])
    def test_invalid_severity(self):
        with self.assertRaises(ValueError): timeline(self.history,severity='urgent')
    def test_gate(self):
        data=self.mocked(nodes=10)
        self.assertEqual(data['overall_gate']['selected_policy'],'default')
        self.assertFalse(data['production_activation'])
        self.assertEqual(data['category_filters']['nodes'],10)
    def test_export_json(self):
        with tempfile.TemporaryDirectory() as d, patch('campaign_timeline_v533.alert_view',return_value={'alerts':[]}):
            p=Path(d)/'report.json'; export_timeline(self.history,p)
            self.assertEqual(json.loads(p.read_text())['schema'],'storagescope.regression-timeline.v5.33')
    def test_export_csv_md(self):
        with tempfile.TemporaryDirectory() as d, patch('campaign_timeline_v533.alert_view',return_value={'alerts':[]}):
            p=Path(d)/'report.csv'; export_timeline(self.history,p,format='csv')
            with p.open(newline='', encoding='utf-8') as stream:
                self.assertEqual(len(list(csv.reader(stream))), 1)
            p=Path(d)/'report.md'; export_timeline(self.history,p,format='md')
            self.assertIn('Abdelhalim Talbi',p.read_text())
    def test_invalid_export(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): export_timeline(self.history,Path(d)/'bad',format='html')
