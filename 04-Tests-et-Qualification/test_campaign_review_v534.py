import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from campaign_review_v534 import timeline_plot, review_dossier

class History:
    def list(self, limit): return [{'id': x,'recorded_at':'2026-10-16T12:00:00Z','sha256':x*64} for x in 'ab']
    def report(self, limit): return {'selected_policy':'default','reason':'test'}

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.history=History()
        self.event={'severity':'warning','code':'paired_degradation','count':2,'evidence_ids':['m1'],'evidence_coverage':'partial'}
    def mock(self): return patch('campaign_timeline_v533.alert_view',return_value={'alerts':[self.event]})
    def test_empty_plot(self): self.assertEqual(timeline_plot({'events':[]})['points'],[])
    def test_coordinates(self):
        p=timeline_plot({'events':[{'severity':'critical','code':'regression','count':2,'later_id':'b'}]})
        self.assertEqual(len(p['points']),1)
        self.assertFalse(p['production_activation'])
    def test_invalid_width(self):
        with self.assertRaises(ValueError): timeline_plot({'events':[]},width=200)
    def test_invalid_severity(self):
        with self.assertRaises(ValueError): timeline_plot({'events':[{'severity':'unknown','count':1}]})
    def test_invalid_count(self):
        with self.assertRaises(ValueError): timeline_plot({'events':[{'severity':'info','count':-1}]})
    def test_export_manifest(self):
        with tempfile.TemporaryDirectory() as d,self.mock():
            p=Path(d)/'review.zip'; result=review_dossier(self.history,p)
            self.assertEqual(result['files'],7)
            with zipfile.ZipFile(p) as z:
                manifest=json.loads(z.read('MANIFEST-SHA256.json'))
                self.assertFalse(manifest['production_activation'])
                for name,digest in manifest['files'].items():
                    self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(),digest)
    def test_export_events(self):
        with tempfile.TemporaryDirectory() as d,self.mock():
            p=Path(d)/'review.zip'; review_dossier(self.history,p)
            with zipfile.ZipFile(p) as z:
                self.assertEqual(len(json.loads(z.read('chronologie.json'))['events']),1)
    def test_export_atomic_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'review.zip'; p.write_bytes(b'original')
            with self.mock(), patch('campaign_timeline_v533.export_timeline',side_effect=RuntimeError('failed')):
                with self.assertRaises(RuntimeError): review_dossier(self.history,p)
            self.assertEqual(p.read_bytes(),b'original')
            self.assertEqual(sorted(x.name for x in Path(d).iterdir()),['review.zip'])
    def test_filtered_gate(self):
        with tempfile.TemporaryDirectory() as d,self.mock():
            p=Path(d)/'review.zip'; review_dossier(self.history,p,severity='warning')
            with zipfile.ZipFile(p) as z:
                data=json.loads(z.read('chronologie.json'))
                self.assertEqual(data['overall_gate']['selected_policy'],'default')
                self.assertTrue(data['filter_is_descriptive_only'])
