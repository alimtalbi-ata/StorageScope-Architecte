"""Regression: malformed duplicate observations must not certify NAS shares.

Synthetic fixtures only. Author: Abdelhalim Talbi.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from vendor_snapshot_import_v6201 import main, normalize

GIB = 1073741824


def snapshot(vendor):
    columns = {
        'netapp_ontap': ('serial_number', 'capacity_used_bytes', 'capacity_total_bytes', 'volumes', 'uuid'),
        'dell_powerscale': ('serial', 'used_bytes', 'total_bytes', 'exports', 'id'),
        'pure_flashblade': ('array_id', 'space_used_bytes', 'space_total_bytes', 'shares', 'id'),
    }
    serial, used, total, shares, share_id = columns[vendor]
    good = {share_id: 'share-01', 'protocol': 'NFS', 'used_bytes': 2*GIB, 'quota_bytes': 4*GIB}
    bad = copy.deepcopy(good)
    bad['used_bytes'] = 4*GIB + 1
    return {'schema': 'storagescope.vendor-snapshot.v1', 'vendor': vendor,
            'source_ref': 'synthetic-contract', 'collected_at': '2026-10-23T20:00:00Z',
            'systems': [{serial: 'SN-001', used: 8*GIB, total: 10*GIB,
                         shares: [good, bad]}]}


class ShareConflictTests(unittest.TestCase):
    def test_valid_and_invalid_duplicate_quarantined_in_both_orders(self):
        for vendor in ('netapp_ontap', 'dell_powerscale', 'pure_flashblade'):
            for reversed_order in (False, True):
                with self.subTest(vendor=vendor, reversed_order=reversed_order):
                    data = snapshot(vendor)
                    shares_key = {'netapp_ontap': 'volumes', 'dell_powerscale': 'exports',
                                  'pure_flashblade': 'shares'}[vendor]
                    if reversed_order:
                        data['systems'][0][shares_key].reverse()
                    before = copy.deepcopy(data)
                    report = normalize(data)
                    self.assertEqual(data, before)
                    self.assertEqual(report['assessment'], 'INCOMPLETE')
                    self.assertEqual(len(report['topology']['assets']), 1)
                    self.assertEqual(report['topology']['shares'], [])
                    self.assertTrue(any('conflicting duplicate share evidence' in r
                                        for r in report['rejected']))
                    self.assertEqual(report['automatic_changes'], 0)

    def test_unrelated_valid_share_also_quarantined_on_ambiguous_system(self):
        data = snapshot('netapp_ontap')
        data['systems'][0]['volumes'].append({'uuid': 'unrelated', 'protocol': 'SMB',
                                              'used_bytes': GIB, 'quota_bytes': 2*GIB})
        report = normalize(data)
        self.assertEqual(report['topology']['shares'], [])
        self.assertEqual(report['assessment'], 'INCOMPLETE')

    def test_exclusive_cli_output_preserves_source_and_report_on_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp, out = Path(tmp) / 'vendor.json', Path(tmp) / 'evidence.json'
            data = snapshot('pure_flashblade')
            inp.write_text(json.dumps(data), encoding='utf-8')
            self.assertEqual(main([str(inp), str(out)]), 0)
            first = out.read_bytes()
            self.assertEqual(json.loads(first)['topology']['shares'], [])
            with self.assertRaises(FileExistsError):
                main([str(inp), str(out)])
            self.assertEqual(out.read_bytes(), first)
            self.assertEqual(json.loads(inp.read_text(encoding='utf-8')), data)


if __name__ == '__main__':
    unittest.main()
