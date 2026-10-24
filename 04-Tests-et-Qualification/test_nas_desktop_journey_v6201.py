"""Real NAS import -> view model -> CSV round-trip (no Tk display required)."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from vendor_snapshot_import_v6201 import load_snapshot, normalize
from nas_inventory_desktop_v6201 import inventory_rows, export_inventory_csv

GIB = 1073741824


class NasDesktopJourney(unittest.TestCase):
    def test_import_display_and_export(self):
        sample = {
            'schema': 'storagescope.vendor-snapshot.v1', 'vendor': 'netapp_ontap',
            'source_ref': 'lab-qualification', 'collected_at': '2026-10-24T10:00:00Z',
            'systems': [
                {'serial_number': 'SN-1', 'cluster_name': '=HYPERLINK("bad")',
                 'capacity_used_bytes': 20 * GIB, 'capacity_total_bytes': 100 * GIB,
                 'volumes': [
                     {'uuid': 'vol1', 'protocol': 'NFS', 'used_bytes': 10 * GIB},
                     {'uuid': 'vol2', 'protocol': 'SMB', 'used_bytes': 5 * GIB}]},
                {'serial_number': 'SN-2', 'cluster_name': 'nas-secondary',
                 'capacity_used_bytes': 1 * GIB, 'capacity_total_bytes': 2 * GIB,
                 'volumes': []},
            ]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / 'snapshot.json', root / 'inventory.csv'
            source.write_text(json.dumps(sample), encoding='utf-8')
            original = source.read_bytes()
            report = normalize(load_snapshot(source))
            rows, shares = inventory_rows(report)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0][5], 2)
            self.assertEqual(rows[1][5], 0)
            self.assertEqual({share['protocol'] for share in shares[rows[0][2]]}, {'NFS', 'SMB'})
            self.assertEqual(export_inventory_csv(rows, target), target)
            with target.open(encoding='utf-8-sig', newline='') as stream:
                parsed = list(csv.reader(stream, delimiter=';'))
            self.assertEqual(len(parsed), 3)
            self.assertTrue(parsed[1][1].startswith("'="))
            self.assertEqual(parsed[1][2], 'netapp_ontap:SN-1')
            self.assertEqual(source.read_bytes(), original)
            previous = target.read_bytes()
            with self.assertRaises(FileExistsError):
                export_inventory_csv(rows, target)
            self.assertEqual(target.read_bytes(), previous)
            self.assertFalse(list(root.glob('.storagescope-*.tmp')))


if __name__ == '__main__':
    unittest.main()
