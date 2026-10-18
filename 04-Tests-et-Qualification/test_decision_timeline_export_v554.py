"""Filtered export regression tests. Author: Abdelhalim Talbi."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from decision_qualification_v547 import QualificationStore
from decision_timeline_export_v554 import filtered_timeline, export_timeline

class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)
        self.store=QualificationStore(str(self.path/'db.sqlite'))
        self.store.create('D1','subject','owner','2026-12-01','REF')
    def qualify(self):
        self.store.qualify('D1','reviewer','ACCEPT',dict.fromkeys(('traceability','relevance','integrity','coverage'),True),'documented')
    def test_all(self): self.assertEqual(filtered_timeline(self.store,'D1')['total_events'],1)
    def test_event_filter(self): self.assertEqual(filtered_timeline(self.store,'D1',event_type='EVIDENCE_QUALIFIED')['visible_events'],0)
    def test_state_filter(self): self.assertEqual(filtered_timeline(self.store,'D1',state='CURRENT')['visible_events'],0)
    def test_qualification_filter(self):
        self.qualify(); self.assertEqual(filtered_timeline(self.store,'D1',state='CURRENT')['visible_events'],1)
    def test_invalid_state(self):
        with self.assertRaises(ValueError):filtered_timeline(self.store,'D1',state='WRONG')
    def test_invalid_type(self):
        with self.assertRaises(ValueError):filtered_timeline(self.store,'D1',event_type='')
    def test_json(self):
        p=self.path/'out.json';export_timeline(self.store,'D1',p)
        self.assertEqual(json.loads(p.read_text())['decision_id'],'D1')
    def test_csv(self):
        self.qualify();p=self.path/'out.csv';export_timeline(self.store,'D1',p,format='csv',state='CURRENT')
        with p.open(newline='') as f: self.assertEqual(len(list(csv.reader(f))),2)
    def test_unknown_format(self):
        with self.assertRaises(ValueError):export_timeline(self.store,'D1',self.path/'out',format='xml')
    def test_unknown_decision(self):
        with self.assertRaises(KeyError):filtered_timeline(self.store,'MISSING')
    def test_no_activation(self):self.assertFalse(filtered_timeline(self.store,'D1')['production_activation'])
