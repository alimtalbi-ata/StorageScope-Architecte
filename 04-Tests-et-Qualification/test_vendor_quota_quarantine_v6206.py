"""V6.206: unique malformed share quotas quarantine all NAS share evidence.
All fixtures synthetic. Author: Abdelhalim Talbi.
"""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '03-Sources'))
from vendor_snapshot_import_v6201 import main, normalize

GIB = 1073741824
KEYS = {
    'netapp_ontap': ('serial_number', 'capacity_used_bytes', 'capacity_total_bytes', 'volumes', 'uuid'),
    'dell_powerscale': ('serial', 'used_bytes', 'total_bytes', 'exports', 'id'),
    'pure_flashblade': ('array_id', 'space_used_bytes', 'space_total_bytes', 'shares', 'id'),
}


def snapshot(vendor, defect='overrun'):
    serial, used, total, shares_key, share_id = KEYS[vendor]
    good = {share_id: 'good', 'protocol': 'NFS', 'used_bytes': GIB, 'quota_bytes': 2 * GIB}
    bad = {share_id: 'bad', 'protocol': 'SMB', 'used_bytes': 3 * GIB, 'quota_bytes': 4 * GIB}
    if defect == 'overrun':
        bad['used_bytes'] = 4 * GIB + 1
    elif defect == 'invalid_type':
        bad['quota_bytes'] = True
    else:
        raise ValueError(defect)
    return {'schema': 'storagescope.vendor-snapshot.v1', 'vendor': vendor,
            'source_ref': 'synthetic-v6206', 'collected_at': '2026-10-24T01:00:00Z',
            'systems': [{serial: 'NAS-01', used: 10 * GIB, total: 20 * GIB,
                         shares_key: [good, bad]}]}


class QuotaQuarantineTests(unittest.TestCase):
    def test_unique_malformed_share_quarantines_all_shares_in_any_order(self):
        for vendor in KEYS:
            for defect in ('overrun', 'invalid_type'):
                for reverse in (False, True):
                    with self.subTest(vendor=vendor, defect=defect, reverse=reverse):
                        data = snapshot(vendor, defect)
                        if reverse:
                            data['systems'][0][KEYS[vendor][3]].reverse()
                        before = copy.deepcopy(data)
                        result = normalize(data)
                        self.assertEqual(data, before)
                        self.assertEqual(result['assessment'], 'INCOMPLETE')
                        self.assertEqual(result['topology']['shares'], [])
                        self.assertEqual(result['quarantined_share_asset_ids'], [f'{vendor}:NAS-01'])
                        self.assertEqual(len(result['topology']['assets']), 1)
                        self.assertEqual(result['automatic_changes'], 0)
                        self.assertTrue(any('quota' in reason for reason in result['rejected']))

    def test_unaffected_nas_retains_its_verified_share(self):
        for vendor in KEYS:
            with self.subTest(vendor=vendor):
                data = snapshot(vendor)
                serial, _, _, shares_key, share_id = KEYS[vendor]
                data['systems'].append({serial: 'NAS-02', shares_key: [
                    {share_id: 'clean', 'protocol': 'NFS', 'used_bytes': GIB, 'quota_bytes': 2 * GIB}]})
                report = normalize(data)
                self.assertEqual(report['quarantined_share_asset_ids'], [f'{vendor}:NAS-01'])
                self.assertEqual(len(report['topology']['shares']), 1)
                self.assertEqual(report['topology']['shares'][0]['nas_id'], f'{vendor}:NAS-02')
                self.assertEqual(report['assessment'], 'INCOMPLETE')

    def test_clean_nas_preserves_all_shares(self):
        for vendor in KEYS:
            with self.subTest(vendor=vendor):
                data = snapshot(vendor)
                _, _, _, shares_key, _ = KEYS[vendor]
                data['systems'][0][shares_key][1]['used_bytes'] = 3 * GIB
                report = normalize(data)
                self.assertEqual(report['assessment'], 'OBSERVED_ONLY')
                self.assertEqual(report['quarantined_share_asset_ids'], [])
                self.assertEqual(len(report['topology']['shares']), 2)

    def test_cli_digest_quarantine_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory) / 'snapshot.json'
            dst = Path(directory) / 'report.json'
            raw = json.dumps(snapshot('netapp_ontap')).encode('utf-8')
            src.write_bytes(raw)
            self.assertEqual(main([str(src), str(dst)]), 0)
            report = json.loads(dst.read_text(encoding='utf-8'))
            self.assertEqual(report['snapshot_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(report['topology']['shares'], [])
            self.assertEqual(report['quarantined_share_asset_ids'], ['netapp_ontap:NAS-01'])
            old_report = dst.read_bytes()
            with self.assertRaises(FileExistsError):
                main([str(src), str(dst)])
            self.assertEqual(dst.read_bytes(), old_report)
            self.assertEqual(src.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
