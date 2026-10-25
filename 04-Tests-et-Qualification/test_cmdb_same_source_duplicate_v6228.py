"""V6.228 CMDB same-source duplicate evidence quarantine.
Synthetic fixtures. Author: Abdelhalim Talbi.
"""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('inventory_reconcile_v619', ROOT / '03-Sources' / 'inventory_reconcile_v619.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
import sys
sys.path.insert(0, str(ROOT / '03-Sources'))
from cmdb_review_desktop_v6198 import review_cmdb_file, format_cmdb_report


class SameSourceDuplicateTests(unittest.TestCase):
    def test_same_source_same_serial_quarantined(self):
        report = mod.reconcile([
            {'source': 'NetApp', 'kind': 'storage_array', 'serial': 'S1'},
            {'source': ' netapp ', 'kind': 'array', 'serial': 's1'},
        ])
        self.assertEqual(report['assessment'], 'INCOMPLETE')
        self.assertEqual(report['candidates'][0]['action'], 'QUARANTINE_DUPLICATE_SOURCE_OBSERVATION')
        self.assertEqual(report['duplicate_source_indices'], [0, 1])
        self.assertEqual(report['quarantined_indices'], [0, 1])
        self.assertEqual(report['automatic_merges'], 0)

    def test_same_source_conflict_keeps_identity_conflict_priority(self):
        report = mod.reconcile([
            {'source': 'Pure', 'serial': 'S1', 'wwn': 'A'},
            {'source': 'pure', 'serial': 's1', 'wwn': 'B'},
        ])
        self.assertEqual(report['candidates'][0]['action'], 'QUARANTINE_IDENTITY_CONFLICT')
        self.assertEqual(report['duplicate_source_indices'], [0, 1])

    def test_quarantine_propagates_to_independent_source(self):
        records = [
            {'source': 'NetApp', 'serial': 'S1'},
            {'source': 'NetApp', 'serial': 's1'},
            {'source': 'CMDB', 'serial': 'S1'},
        ]
        original = copy.deepcopy(records)
        report = mod.reconcile(records)
        self.assertEqual(report['quarantined_indices'], [0, 1, 2])
        self.assertEqual(report['duplicate_source_indices'], [0, 1])
        self.assertEqual(report['propagated_quarantine_indices'], [2])
        self.assertEqual(report['candidates'][0]['action'], 'QUARANTINE_DUPLICATE_SOURCE_OBSERVATION')
        self.assertTrue(all(c['action'] != 'REVIEW_REQUIRED' for c in report['candidates']))
        self.assertEqual(records, original)

    def test_distinct_sources_remain_review_only(self):
        report = mod.reconcile([{'source': 'NetApp', 'serial': 'S1'}, {'source': 'CMDB', 'serial': 's1'}])
        self.assertEqual(report['assessment'], 'REVIEW_REQUIRED')
        self.assertEqual(report['duplicate_source_indices'], [])
        self.assertEqual(report['candidates'][0]['action'], 'REVIEW_REQUIRED')

    def test_desktop_json_report_exposes_duplicate_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'cmdb.json'
            path.write_text(json.dumps([{'source': 'NetApp', 'serial': 'S1'},
                                        {'source': 'netapp', 'serial': 's1'}]), encoding='utf-8')
            report = review_cmdb_file(path)
            self.assertEqual(report['duplicate_source_indices'], [0, 1])
            display = format_cmdb_report(report)
            self.assertIn('QUARANTINE_DUPLICATE_SOURCE_OBSERVATION', display)
            self.assertIn('Doublons intra-source', display)


if __name__ == '__main__':
    unittest.main()
