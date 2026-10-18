import csv
import json
import tempfile
import unittest
from pathlib import Path
from campaign_history_v526 import CampaignHistory
from campaign_report_v530 import comparison_report, export_report
from test_campaign_compare_v528 import campaign

class ReportV530Tests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.path = Path(t.name)
        self.history = CampaignHistory(self.path/'history.sqlite')
        self.history.add(campaign('a', .1)); self.history.add(campaign('b', .2))
    def test_summary_and_provenance(self):
        r = comparison_report(self.history, 'a', 'b')
        self.assertEqual(r['matched_count'], 12)
        self.assertEqual(len(r['campaigns'][0]['sha256']), 64)
    def test_json_export(self):
        path=self.path/'report.json'; info=export_report(self.history,'a','b',path)
        self.assertEqual(info['format'],'json')
        self.assertFalse(json.loads(path.read_text())['production_activation'])
    def test_csv_export(self):
        path=self.path/'report.csv'; export_report(self.history,'a','b',path,format='csv')
        with path.open(newline='') as f: self.assertEqual(len(list(csv.DictReader(f))),12)
    def test_markdown_export(self):
        path=self.path/'report.md'; export_report(self.history,'a','b',path,format='md')
        self.assertIn('SHA-256',path.read_text())
    def test_invalid_format_preserves_existing_file(self):
        path=self.path/'report';path.write_text('unchanged')
        with self.assertRaises(ValueError):export_report(self.history,'a','b',path,format='pdf')
        self.assertEqual(path.read_text(),'unchanged')
    def test_invalid_campaign_no_export(self):
        path=self.path/'report.json'
        with self.assertRaises(ValueError):export_report(self.history,'a','x',path)
        self.assertFalse(path.exists())
    def test_filtered_does_not_change_gate(self):
        a=comparison_report(self.history,'a','b')
        b=comparison_report(self.history,'a','b',nodes=999)
        self.assertEqual(a['overall_gate'],b['overall_gate'])
    def test_export_digest(self):
        import hashlib
        path=self.path/'report.json';info=export_report(self.history,'a','b',path)
        self.assertEqual(info['sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
