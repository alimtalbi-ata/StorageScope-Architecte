"""SQLite contention and crash-safe export regression tests, v6.17."""
import concurrent.futures
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from campaign_history_v526 import CampaignHistory
from architecture_decisions_v536 import DecisionStore
from test_campaign_history_v526 import campaign

class ConcurrencyAndExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_concurrent_identical_campaign_only_one_insert(self):
        path = self.root / 'campaigns.db'
        def write(_): return CampaignHistory(path).add(campaign('shared'))
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(write, range(16)))
        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), 15)
        self.assertEqual(len(CampaignHistory(path).list()), 1)

    def test_concurrent_conflicting_campaign_is_immutable(self):
        path = self.root / 'campaigns.db'
        CampaignHistory(path).add(campaign('shared'))
        def write(i):
            try: return CampaignHistory(path).add(campaign('shared', .2 if i % 2 else .12))
            except ValueError: return 'conflict'
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(write, range(16)))
        self.assertEqual(results.count('conflict'), 8)
        self.assertEqual(results.count(False), 8)
        self.assertEqual(len(CampaignHistory(path).list()), 1)

    def test_concurrent_distinct_campaigns_no_lost_writes(self):
        path = self.root / 'campaigns.db'
        CampaignHistory(path)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            self.assertTrue(all(pool.map(lambda i: CampaignHistory(path).add(campaign(str(i))), range(16))))
        self.assertEqual(len(CampaignHistory(path).list()), 16)

    def test_export_failure_preserves_existing_report(self):
        history = CampaignHistory(self.root / 'campaigns.db')
        target = self.root / 'report.json'
        target.write_text('existing report', encoding='utf-8')
        with patch('campaign_history_v526.os.replace', side_effect=OSError('disk error')):
            with self.assertRaises(OSError): history.export_json(target)
        self.assertEqual(target.read_text(encoding='utf-8'), 'existing report')
        self.assertEqual(list(self.root.glob('.report.json.*.tmp')), [])

    def test_export_success_replaces_and_is_valid_json(self):
        history = CampaignHistory(self.root / 'campaigns.db')
        history.add(campaign('one'))
        target = self.root / 'reports' / 'report.json'
        history.export_json(target)
        self.assertEqual(json.loads(target.read_text(encoding='utf-8'))['campaign_count'], 1)
        self.assertEqual(list(target.parent.glob('*.tmp')), [])

if __name__ == '__main__': unittest.main()
