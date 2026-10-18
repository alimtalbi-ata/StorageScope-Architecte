import json
import tempfile
import unittest
from pathlib import Path
from decision_committee_dashboard_v560 import committee_dashboard_v560,export_committee_dashboard
from decision_committee_resolution_v558 import CommitteeResolutionStore

class CommitteeDashboardV560Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=CommitteeResolutionStore(str(Path(self.tmp.name)/'test.db'))
    def tearDown(self):self.tmp.cleanup()
    def test_empty(self):self.assertEqual(committee_dashboard_v560(self.store)['total'],0)
    def test_no_activation(self):self.assertFalse(committee_dashboard_v560(self.store)['production_activation'])
    def test_schema(self):self.assertIn('v5.60',committee_dashboard_v560(self.store)['schema'])
    def test_bad_verdict(self):
        with self.assertRaises(ValueError):committee_dashboard_v560(self.store,verdict='ACCEPT')
    def test_bad_priority(self):
        with self.assertRaises(ValueError):committee_dashboard_v560(self.store,priority='P0')
    def test_bad_deadline(self):
        with self.assertRaises(ValueError):committee_dashboard_v560(self.store,deadline='yesterday')
    def test_empty_filtered(self):self.assertEqual(committee_dashboard_v560(self.store,verdict='DEFER')['deferred'],0)
    def test_json_export(self):
        dest=Path(self.tmp.name)/'out.json'
        export_committee_dashboard(self.store,dest,format='json')
        self.assertEqual(json.loads(dest.read_text())['total'],0)
    def test_csv_export(self):
        dest=Path(self.tmp.name)/'out.csv'
        export_committee_dashboard(self.store,dest)
        self.assertIn('committee_verdict',dest.read_text())
    def test_bad_export(self):
        with self.assertRaises(ValueError):export_committee_dashboard(self.store,Path(self.tmp.name)/'x',format='xml')
    def test_ui(self):
        source=Path(__file__).with_name('decision_workspace_ui_v543.py').read_text()
        self.assertIn('committee_dashboard_v560',source)
        self.assertIn("text='Filtrer'",source)
