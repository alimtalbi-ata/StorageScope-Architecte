"""V6.230: manufacturer-aware CMDB reconciliation; synthetic fixtures only.
Author: Abdelhalim Talbi.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '03-Sources'))
from inventory_reconcile_v619 import reconcile
from cmdb_review_desktop_v6198 import review_cmdb_file, format_cmdb_report


class ManufacturerIdentityTests(unittest.TestCase):
    def test_serial_collision_across_manufacturers_quarantined(self):
        records = [{'source': 'CMDB', 'serial': '1234', 'manufacturer': 'NetApp'},
                   {'source': 'collector', 'serial': '1234', 'vendor': 'Pure Storage'}]
        original = copy.deepcopy(records)
        result = reconcile(records)
        self.assertEqual(result['assessment'], 'INCOMPLETE')
        self.assertEqual(result['quarantined_indices'], [0, 1])
        self.assertEqual(result['candidates'][0]['action'], 'QUARANTINE_IDENTITY_CONFLICT')
        self.assertIn({'field': 'manufacturer', 'left': 'netapp', 'right': 'pure storage'},
                      result['candidates'][0]['identity_conflicts'])
        self.assertEqual(result['automatic_merges'], 0)
        self.assertEqual(records, original)

    def test_matching_vendor_alias_fields_are_review_only(self):
        result = reconcile([{'source': 'CMDB', 'serial': 'S1', 'vendor': '  PURE   STORAGE '},
                            {'source': 'collector', 'serial': 's1', 'manufacturer': 'pure storage'}])
        self.assertEqual(result['candidates'][0]['action'], 'REVIEW_REQUIRED')
        self.assertEqual(result['quarantined_indices'], [])

    def test_conflicting_vendor_fields_in_one_record_invalid(self):
        result = reconcile([{'source': 'a', 'serial': 'S1', 'vendor': 'NetApp', 'manufacturer': 'IBM'},
                            {'source': 'b', 'serial': 'S1', 'vendor': 'NetApp'}])
        self.assertEqual(result['invalid_records'], [{'index': 0, 'reason': 'conflicting_manufacturer'}])
        self.assertEqual(result['candidate_count'], 0)

    def test_non_string_vendor_is_not_match_evidence(self):
        for bad in (0, False, [], {}, ''):
            with self.subTest(bad=bad):
                result = reconcile([{'source': 'a', 'serial': 'S1', 'vendor': bad},
                                    {'source': 'b', 'serial': 'S1'}])
                self.assertEqual(result['invalid_records'], [{'index': 0, 'reason': 'invalid_manufacturer'}])
                self.assertEqual(result['candidate_count'], 0)

    def test_unknown_or_absent_manufacturer_does_not_infer_match(self):
        result = reconcile([{'source': 'a', 'serial': 'S1', 'vendor': 'N/A'},
                            {'source': 'b', 'serial': 'S1', 'manufacturer': 'NetApp'}])
        self.assertEqual(result['candidates'][0]['action'], 'REVIEW_REQUIRED')

    def test_conflict_propagates_without_tainting_unrelated_devices(self):
        result = reconcile([{'source': 'a', 'serial': 'S1', 'vendor': 'NetApp'},
                            {'source': 'b', 'serial': 'S1', 'vendor': 'Pure'},
                            {'source': 'c', 'serial': 'S1'},
                            {'source': 'd', 'serial': 'S2', 'vendor': 'NetApp'},
                            {'source': 'e', 'serial': 'S2', 'vendor': 'NetApp'}])
        self.assertEqual(result['quarantined_indices'], [0, 1, 2])
        self.assertEqual(result['propagated_quarantine_indices'], [2])
        self.assertEqual(next(c for c in result['candidates'] if c['indices'] == [3, 4])['action'], 'REVIEW_REQUIRED')

    def test_desktop_report_retains_manufacturer_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'snapshot.json'
            raw = json.dumps([{'source': 'a', 'serial': 'S1', 'vendor': 'IBM'},
                              {'source': 'b', 'serial': 'S1', 'manufacturer': 'HPE'}]).encode('utf-8')
            path.write_bytes(raw)
            report = review_cmdb_file(path)
            self.assertEqual(report['assessment'], 'INCOMPLETE')
            self.assertIn('manufacturer', format_cmdb_report(report))
            self.assertEqual(path.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
