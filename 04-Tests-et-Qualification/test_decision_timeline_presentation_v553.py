"""Regression tests for the human-readable v5.53 timeline."""
import ast
import tempfile
import unittest
from pathlib import Path
from decision_qualification_v547 import QualificationStore
from decision_timeline_presentation_v553 import timeline_presentation, STATUS

class TimelinePresentationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.store=QualificationStore(str(Path(self.temp.name)/'qual.db'))
        self.store.create('D1','Subject','owner','2026-12-01','REF')
    def qualify(self, verdict='ACCEPT'):
        self.store.qualify('D1','reviewer',verdict,dict.fromkeys(('traceability','relevance','integrity','coverage'),True),'Reason')
    def test_unreviewed(self): self.assertEqual(timeline_presentation(self.store,'D1')['current_state'],'UNREVIEWED')
    def test_accepted(self):
        self.qualify(); self.assertEqual(timeline_presentation(self.store,'D1')['current_state'],'CURRENT')
    def test_review_count(self):
        self.qualify();self.qualify('REJECT');self.assertEqual(timeline_presentation(self.store,'D1')['review_count'],2)
    def test_historical(self):
        self.qualify();self.qualify('REJECT');self.assertEqual([x['state'] for x in timeline_presentation(self.store,'D1')['events'] if x['type']=='EVIDENCE_QUALIFIED'],['HISTORICAL','CURRENT'])
    def test_no_activation(self): self.assertFalse(timeline_presentation(self.store,'D1')['production_activation'])
    def test_not_sufficiency(self): self.assertFalse(timeline_presentation(self.store,'D1')['evidence_sufficiency_verified'])
    def test_unknown(self):
        with self.assertRaises(KeyError):timeline_presentation(self.store,'MISSING')
    def test_labels(self): self.assertTrue(all(label and color.startswith('#') for label,color in STATUS.values()))
    def test_ui(self):
        source=(Path(__file__).parent/'decision_workspace_ui_v543.py').read_text();ast.parse(source)
        self.assertIn('filtered_timeline(store,ident)',source)
        self.assertIn('grid.tag_configure(state,foreground=color)',source)
