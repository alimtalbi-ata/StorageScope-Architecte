"""V6.207: malformed NAS share records invalidate the entire NAS share set.

All fixtures are synthetic; no CMDB/vendor access. Author: Abdelhalim Talbi.
"""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from vendor_snapshot_import_v6201 import normalize

GIB = 1073741824
VENDORS = {
    'netapp_ontap': ('serial_number', 'volumes', 'uuid'),
    'dell_powerscale': ('serial', 'exports', 'id'),
    'pure_flashblade': ('array_id', 'shares', 'id'),
}


def fixture(vendor, malformed, reverse=False):
    serial_key, shares_key, share_key = VENDORS[vendor]
    valid = {share_key: 'clean', 'protocol': 'NFS',
             'used_bytes': GIB, 'quota_bytes': 2 * GIB}
    entries = [valid, malformed]
    if reverse:
        entries.reverse()
    return {
        'schema': 'storagescope.vendor-snapshot.v1',
        'vendor': vendor, 'source_ref': 'synthetic-v6207',
        'collected_at': '2026-10-24T02:00:00Z',
        'systems': [
            {serial_key: 'NAS-01', shares_key: entries},
            {serial_key: 'NAS-02', shares_key: [
                {share_key: 'safe', 'protocol': 'SMB',
                 'used_bytes': GIB, 'quota_bytes': 2 * GIB}]},
        ],
    }


class MalformedShareQuarantineTests(unittest.TestCase):
    def test_malformed_nonobject_share_quarantines_entire_nas_in_both_orders(self):
        for vendor in VENDORS:
            for malformed in (None, 42, 'broken', [], ['unexpected']):
                for reverse in (False, True):
                    with self.subTest(vendor=vendor, malformed=malformed, reverse=reverse):
                        data = fixture(vendor, malformed, reverse)
                        original = copy.deepcopy(data)
                        report = normalize(data)
                        self.assertEqual(data, original)
                        self.assertEqual(report['assessment'], 'INCOMPLETE')
                        self.assertEqual(report['quarantined_share_asset_ids'],
                                         [f'{vendor}:NAS-01'])
                        self.assertEqual(len(report['topology']['assets']), 2)
                        self.assertEqual([s['nas_id'] for s in report['topology']['shares']],
                                         [f'{vendor}:NAS-02'])
                        self.assertTrue(any('not an object' in r for r in report['rejected']))
                        self.assertEqual(report['automatic_changes'], 0)

    def test_clean_share_records_remain_available(self):
        for vendor, (serial_key, shares_key, share_key) in VENDORS.items():
            with self.subTest(vendor=vendor):
                data = fixture(vendor, None)
                data['systems'][0][shares_key].pop()
                report = normalize(data)
                self.assertEqual(report['assessment'], 'OBSERVED_ONLY')
                self.assertEqual(report['quarantined_share_asset_ids'], [])
                self.assertEqual(len(report['topology']['shares']), 2)


if __name__ == '__main__':
    unittest.main()
