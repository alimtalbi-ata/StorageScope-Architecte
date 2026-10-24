"""V6.212: missing SAN fabric evidence cannot be hidden by an active alternate path.

All fixtures synthetic, read-only. Author: Abdelhalim Talbi.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from storage_path_risk_v6194 import assess
from storage_dependency_impact_v6199 import map_dependencies
from storage_risk_desktop_v6196 import assess_topology_file, format_risk_report


def topology():
    return {
        'schema': 'storagescope.storage-topology.v1',
        'assets': [{'id': 'h1', 'kind': 'host'},
                   {'id': 'a1', 'kind': 'storage_array', 'used_gib': 20, 'total_gib': 100}],
        'paths': [{'host_id': 'h1', 'storage_id': 'a1', 'fabric': 'B', 'port': 'p2', 'state': 'up'}],
        'shares': [],
    }


class MissingFabricEvidenceTests(unittest.TestCase):
    def report(self, data):
        return map_dependencies(data, assess(data))

    def test_missing_fabric_and_healthy_alternate_are_mixed(self):
        data = topology()
        data['paths'].append({'host_id': 'h1', 'storage_id': 'a1', 'state': 'up'})
        result = self.report(data)
        self.assertEqual(result['verified_host_relationships'], 1)
        self.assertEqual(result['unverified_host_relationships'], 1)
        self.assertEqual(result['mixed_evidence_host_relationships'], 1)
        self.assertEqual(result['assets'][0]['mixed_evidence_host_ids'], ['h1'])
        self.assertEqual(result['assessment'], 'INCOMPLETE')
        self.assertEqual(result['automatic_changes'], 0)

    def test_missing_fabric_alone_is_not_verified(self):
        data = topology()
        data['paths'] = [{'host_id': 'h1', 'storage_id': 'a1', 'state': 'up'}]
        result = self.report(data)
        self.assertEqual(result['verified_host_relationships'], 0)
        self.assertEqual(result['unverified_host_relationships'], 1)
        self.assertEqual(result['assessment'], 'INCOMPLETE')

    def test_empty_or_nonstring_fabric_cannot_escape_quarantine(self):
        for bad in ('', '   ', 42, None):
            with self.subTest(fabric=bad):
                data = topology()
                data['paths'].append({'host_id': 'h1', 'storage_id': 'a1', 'fabric': bad, 'state': 'up'})
                result = self.report(data)
                self.assertEqual(result['mixed_evidence_host_relationships'], 1)
                self.assertEqual(result['unverified_host_relationships'], 1)

    def test_independent_array_is_unaffected_and_order_independent(self):
        data = topology()
        data['assets'] += [{'id': 'h2', 'kind': 'host'},
                           {'id': 'a2', 'kind': 'storage_array', 'used_gib': 10, 'total_gib': 100}]
        data['paths'] += [{'host_id': 'h1', 'storage_id': 'a1', 'state': 'down'},
                          {'host_id': 'h2', 'storage_id': 'a2', 'fabric': 'C', 'state': 'up'}]
        original = copy.deepcopy(data)
        result = self.report(data)
        self.assertEqual(data, original)
        self.assertEqual(result, self.report(dict(data, paths=list(reversed(data['paths'])))))
        independent = next(a for a in result['assets'] if a['asset_id'] == 'a2')
        self.assertEqual(independent['verified_host_ids'], ['h2'])
        self.assertEqual(independent['unverified_host_ids'], [])

    def test_desktop_projection_preserves_uncertainty(self):
        data = topology()
        data['paths'].append({'host_id': 'h1', 'storage_id': 'a1', 'fabric': '', 'state': 'up'})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'topology.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            report = assess_topology_file(path)
            self.assertEqual(report['dependency_impact']['mixed_evidence_host_relationships'], 1)
            self.assertIn('Relations hôtes à preuves mixtes : 1', format_risk_report(report))


if __name__ == '__main__':
    unittest.main()
