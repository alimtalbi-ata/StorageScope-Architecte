"""V6.204: NAS share quarantine must be explicit in CLI and desktop evidence.

Synthetic fixtures only. Author: Abdelhalim Talbi.
"""
import copy
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


def fixture(vendor, conflicting=True):
    serial, used, total, share_key, sid = KEYS[vendor]
    good = {sid: 'share-01', 'protocol': 'NFS', 'used_bytes': GIB, 'quota_bytes': 2 * GIB}
    shares = [good, copy.deepcopy(good)] if conflicting else [good]
    return {'schema': 'storagescope.vendor-snapshot.v1', 'vendor': vendor,
            'source_ref': 'synthetic-v6204', 'collected_at': '2026-10-24T00:00:00Z',
            'systems': [{serial: 'NAS-01', used: 3 * GIB, total: 8 * GIB, share_key: shares}]}


class QuarantineVisibilityTests(unittest.TestCase):
    def test_three_vendors_report_quarantined_nas_in_both_orders(self):
        for vendor in KEYS:
            for reverse in (False, True):
                with self.subTest(vendor=vendor, reverse=reverse):
                    data = fixture(vendor)
                    if reverse:
                        data['systems'][0][KEYS[vendor][3]].reverse()
                    before = copy.deepcopy(data)
                    report = normalize(data)
                    self.assertEqual(data, before)
                    self.assertEqual(report['assessment'], 'INCOMPLETE')
                    self.assertEqual(report['quarantined_system_ids'], [])
                    self.assertEqual(report['quarantined_share_asset_ids'], [f'{vendor}:NAS-01'])
                    self.assertEqual(report['topology']['shares'], [])
                    self.assertEqual(report['automatic_changes'], 0)

    def test_clean_snapshot_has_no_share_quarantine(self):
        for vendor in KEYS:
            with self.subTest(vendor=vendor):
                report = normalize(fixture(vendor, conflicting=False))
                self.assertEqual(report['assessment'], 'OBSERVED_ONLY')
                self.assertEqual(report['quarantined_share_asset_ids'], [])
                self.assertEqual(len(report['topology']['shares']), 1)

    def test_cli_exports_quarantine_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / 'source.json', Path(directory) / 'report.json'
            source.write_text(json.dumps(fixture('pure_flashblade')), encoding='utf-8')
            original = source.read_bytes()
            self.assertEqual(main([str(source), str(output)]), 0)
            result = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(result['quarantined_share_asset_ids'], ['pure_flashblade:NAS-01'])
            first = output.read_bytes()
            with self.assertRaises(FileExistsError):
                main([str(source), str(output)])
            self.assertEqual(output.read_bytes(), first)
            self.assertEqual(source.read_bytes(), original)

    def test_desktop_shows_separate_share_quarantine_and_asset_quarantine(self):
        source = (ROOT / '03-Sources/storagescope_windows.py').read_text(encoding='utf-8')
        handler = source.split('        def review_vendor_snapshot():', 1)[1].split('        ttk.Button(page, text=', 1)[0]
        self.assertIn('NAS avec partages en quarantaine', handler)
        self.assertIn('NAS dont les partages sont en quarantaine', handler)
        self.assertIn("report['quarantined_share_asset_ids']", handler)
        self.assertIn('Aucune modification de la CMDB ou des équipements.', handler)


if __name__ == '__main__':
    unittest.main()
