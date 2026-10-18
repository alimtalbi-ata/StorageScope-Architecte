"""Tests for v5.51 chronology and UI integration."""
import ast
import tempfile
import unittest
from pathlib import Path
from decision_qualification_v547 import QualificationStore
from decision_timeline_visual_v551 import visual_timeline

class TimelineVisualTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store=QualificationStore(str(Path(self.tmp.name)/'ledger.db'))
        self.store.create('D1','Architecture SAN','expert','2026-12-01','KB-001')
    def test_created(self):
        data=visual_timeline(self.store,'D1')
        self.assertEqual(data['events'][0]['type'],'CREATED')
    def test_no_production(self):
        self.assertFalse(visual_timeline(self.store,'D1')['production_activation'])
    def test_missing_decision(self):
        with self.assertRaises(KeyError): visual_timeline(self.store,'UNKNOWN')
    def test_human_qualification(self):
        self.store.qualify('D1','expert','ACCEPT',dict.fromkeys(('traceability','relevance','integrity','coverage'),True),'Preuves examinées')
        data=visual_timeline(self.store,'D1')
        self.assertEqual(data['events'][-1]['verdict'],'ACCEPT')
        self.assertFalse(data['events'][-1]['stale'])
    def test_event_sequence(self):
        data=visual_timeline(self.store,'D1')
        self.assertEqual([e['sequence'] for e in data['events']],sorted(e['sequence'] for e in data['events']))
    def test_gui_syntax(self):
        ast.parse((Path(__file__).parent/'decision_workspace_ui_v543.py').read_text())
    def test_gui_timeline(self):
        code=(Path(__file__).parent/'decision_workspace_ui_v543.py').read_text()
        self.assertIn('filtered_timeline(store,ident)',code)  # v5.53 wraps visual timeline
        self.assertIn('Chronologie des preuves',code)
    def test_audit_head(self):
        self.assertEqual(len(visual_timeline(self.store,'D1')['audit_head']),64)

if __name__=='__main__':unittest.main()
