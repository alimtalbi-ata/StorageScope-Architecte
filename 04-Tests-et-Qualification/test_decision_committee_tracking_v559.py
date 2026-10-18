import tempfile
import unittest
from pathlib import Path
from decision_committee_tracking_v559 import committee_tracking
from decision_committee_resolution_v558 import CommitteeResolutionStore

class CommitteeTrackingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=CommitteeResolutionStore(str(Path(self.temp.name)/'decisions.db'))
    def tearDown(self):self.temp.cleanup()
    def test_empty(self):
        result=committee_tracking(self.store)
        self.assertEqual(result['total'],0)
        self.assertEqual(result['deferred'],0)
        self.assertFalse(result['production_activation'])
    def test_invalid_priority(self):
        with self.assertRaises(ValueError):committee_tracking(self.store,priority='INVALID')
    def test_invalid_deadline(self):
        with self.assertRaises(ValueError):committee_tracking(self.store,deadline='INVALID')
    def test_invalid_owner(self):
        with self.assertRaises(ValueError):committee_tracking(self.store,owner=' ')
    def test_author(self):self.assertEqual(committee_tracking(self.store)['author'],'Abdelhalim Talbi')
    def test_schema(self):self.assertIn('v5.59',committee_tracking(self.store)['schema'])
    def test_ui_button(self):self.assertIn('Suivi comité',Path(__file__).with_name('decision_workspace_ui_v543.py').read_text())
    def test_ui_history(self):self.assertIn('committee_history',Path(__file__).with_name('decision_workspace_ui_v543.py').read_text())
