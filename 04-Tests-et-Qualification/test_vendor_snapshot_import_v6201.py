"""Synthetic offline vendor snapshot contract tests. Author: Abdelhalim Talbi."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from vendor_snapshot_import_v6201 import normalize, load_snapshot, main
from storage_path_risk_v6194 import assess

GIB = 1073741824


def sample(vendor):
    names = {
        'netapp_ontap': ('serial_number', 'cluster_name', 'capacity_used_bytes', 'capacity_total_bytes', 'volumes', 'uuid'),
        'dell_powerscale': ('serial', 'cluster', 'used_bytes', 'total_bytes', 'exports', 'id'),
        'pure_flashblade': ('array_id', 'name', 'space_used_bytes', 'space_total_bytes', 'shares', 'id'),
    }
    sid, name, used, total, shares, share_id = names[vendor]
    return {'schema': 'storagescope.vendor-snapshot.v1', 'vendor': vendor,
            'source_ref': 'lab-capture-001', 'collected_at': '2026-10-23T20:00:00Z',
            'systems': [{sid: 'SN-1', name: 'array', used: 80*GIB, total: 100*GIB,
                         shares: [{share_id: 'share-1', 'protocol': 'NFS',
                                   'used_bytes': 10*GIB, 'quota_bytes': 20*GIB}]}]}


class VendorSnapshotTests(unittest.TestCase):
    def test_all_three_vendors_normalize_to_risk_schema(self):
        for vendor in ('netapp_ontap', 'dell_powerscale', 'pure_flashblade'):
            with self.subTest(vendor=vendor):
                data = sample(vendor)
                original = copy.deepcopy(data)
                result = normalize(data)
                self.assertEqual(data, original)
                self.assertEqual(result['assessment'], 'OBSERVED_ONLY')
                self.assertEqual(len(result['topology']['assets']), 1)
                self.assertEqual(len(result['topology']['shares']), 1)
                self.assertEqual(result['topology']['assets'][0]['used_gib'], 80)
                self.assertEqual(assess(result['topology'])['schema'], 'storagescope.storage-risk.v1')
                self.assertEqual(result['automatic_changes'], 0)

    def test_duplicate_system_quarantined(self):
        data = sample('netapp_ontap')
        data['systems'].append(copy.deepcopy(data['systems'][0]))
        result = normalize(data)
        self.assertEqual(result['topology']['assets'], [])
        self.assertEqual(result['quarantined_system_ids'], ['SN-1'])
        self.assertEqual(result['assessment'], 'INCOMPLETE')

    def test_missing_provenance_rejected(self):
        data = sample('pure_flashblade')
        del data['source_ref']
        with self.assertRaises(ValueError):
            normalize(data)

    def test_invalid_capacity_rejected_not_silently_zeroed(self):
        data = sample('dell_powerscale')
        data['systems'][0]['used_bytes'] = True
        result = normalize(data)
        self.assertEqual(result['topology']['assets'], [])
        self.assertEqual(result['assessment'], 'INCOMPLETE')

    def test_duplicate_share_poisoned(self):
        data = sample('netapp_ontap')
        data['systems'][0]['volumes'].append(copy.deepcopy(data['systems'][0]['volumes'][0]))
        result = normalize(data)
        self.assertEqual(result['topology']['shares'], [])
        self.assertEqual(result['assessment'], 'INCOMPLETE')

    def test_strict_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'snapshot.json'
            path.write_text('{"vendor":"netapp_ontap","vendor":"pure_flashblade"}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Duplicate JSON'):
                load_snapshot(path)

    def test_invalid_timestamp_rejected(self):
        data = sample('netapp_ontap')
        data['collected_at'] = '2026-10-23T20:00:00+02:00'
        with self.assertRaises(ValueError):
            normalize(data)

    def test_cli_output_exclusive_and_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp, out = Path(tmp) / 'input.json', Path(tmp) / 'report.json'
            data = sample('pure_flashblade')
            inp.write_text(json.dumps(data), encoding='utf-8')
            self.assertEqual(main([str(inp), str(out)]), 0)
            self.assertEqual(json.loads(out.read_text(encoding='utf-8'))['assessment'], 'OBSERVED_ONLY')
            with self.assertRaises(FileExistsError):
                main([str(inp), str(out)])
            self.assertEqual(json.loads(inp.read_text(encoding='utf-8')), data)

    def test_unhashable_vendor_rejected(self):
        data = sample('netapp_ontap')
        data['vendor'] = []
        with self.assertRaises(ValueError):
            normalize(data)

    def test_unsupported_vendor_no_fallback(self):
        data = sample('netapp_ontap')
        data['vendor'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'Unsupported vendor'):
            normalize(data)


if __name__ == '__main__':
    unittest.main()
