"""Regression tests for evidence event navigation v5.52."""
import ast
import tempfile
import unittest
from pathlib import Path
from decision_qualification_v547 import QualificationStore
from decision_evidence_navigation_v552 import evidence_event_navigation

class EvidenceNavigationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store=QualificationStore(str(Path(self.temp.name)/'test.db'))
        self.store.create('D1','Sujet','expert','2026-12-01','KB-001')
    def test_created_reference(self):
        self.assertEqual(evidence_event_navigation(self.store,'D1')['events'][0]['reference'],'KB-001')
    def test_initial_unreviewed(self):
        self.assertTrue(evidence_event_navigation(self.store,'D1')['unreviewed'])
    def test_no_activation(self):
        result=evidence_event_navigation(self.store,'D1')
        self.assertFalse(result['production_activation'])
        self.assertTrue(all(not e['production_activation'] for e in result['events']))
    def test_qualified(self):
        self.store.qualify('D1','expert','ACCEPT',dict.fromkeys(('traceability','relevance','integrity','coverage'),True),'Revue')
        result=evidence_event_navigation(self.store,'D1')
        self.assertEqual(result['events'][-1]['qualification_verdict'],'ACCEPT')
        self.assertFalse(result['unreviewed'])
    def test_unknown(self):
        with self.assertRaises(KeyError):evidence_event_navigation(self.store,'D9')
    def test_invalid_identifier(self):
        with self.assertRaises(ValueError):evidence_event_navigation(self.store,'  ')
    def test_order(self):
        events=evidence_event_navigation(self.store,'D1')['events']
        self.assertEqual([e['sequence'] for e in events],sorted(e['sequence'] for e in events))
    def test_ui_navigation(self):
        code=(Path(__file__).parent/'decision_workspace_ui_v543.py').read_text()
        ast.parse(code)
        self.assertIn('filtered_timeline(store,ident)',code)  # v5.53 delegates navigation through presentation
    def test_ui_clears_detail(self):
        code=(Path(__file__).parent/'decision_workspace_ui_v543.py').read_text()
        self.assertIn("detail.delete('1.0','end')",code)

if __name__=='__main__':unittest.main()
