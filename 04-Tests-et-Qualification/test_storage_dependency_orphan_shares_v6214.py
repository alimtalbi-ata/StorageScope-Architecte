"""V6.214: malformed NAS share evidence is never silently lost.
Synthetic, read-only fixtures. Author: Abdelhalim Talbi.
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
        'assets': [
            {'id': 'n1', 'kind': 'nas', 'used_gib': 10, 'total_gib': 100},
            {'id': 'n2', 'kind': 'nas', 'used_gib': 10, 'total_gib': 100},
        ],
        'paths': [],
        'shares': [{'id': 'good', 'nas_id': 'n1', 'protocol': 'NFS',
                    'used_gib': 1, 'quota_gib': 10}],
    }


class OrphanShareEvidenceTests(unittest.TestCase):
    def report(self, data):
        return map_dependencies(data, assess(data))

    def test_unknown_nas_is_global_only_and_does_not_create_relation(self):
        data = topology()
        data['shares'].append({'id': 'unknown', 'nas_id': 'missing', 'protocol': 'SMB'})
        result = self.report(data)
        self.assertEqual(result['unresolved_share_observations'], 1)
        self.assertEqual(sum(a['unresolved_share_observations'] for a in result['assets']), 0)
        self.assertEqual(result['verified_share_relationships'], 1)
        self.assertEqual(result['assessment'], 'INCOMPLETE')

    def test_missing_id_and_wrong_protocol_attributed_to_trusted_nas(self):
        data = topology()
        data['shares'] += [
            {'nas_id': 'n1', 'protocol': 'SMB'},
            {'id': 'bad-protocol', 'nas_id': 'n1', 'protocol': 'FTP'},
        ]
        result = self.report(data)
        n1 = next(a for a in result['assets'] if a['asset_id'] == 'n1')
        self.assertEqual(n1['unresolved_share_observations'], 2)
        self.assertEqual(n1['verified_share_ids'], ['good'])
        self.assertEqual(result['unresolved_share_observations'], 2)
        self.assertEqual(result['verified_share_relationships'], 1)

    def test_duplicate_share_across_nas_never_verified(self):
        data = topology()
        data['shares'] += [
            {'id': 'dup', 'nas_id': 'n1', 'protocol': 'NFS'},
            {'id': 'dup', 'nas_id': 'n2', 'protocol': 'SMB'},
        ]
        result = self.report(data)
        n1, n2 = result['assets']
        self.assertEqual(result['unresolved_share_observations'], 2)
        self.assertEqual(n1['unresolved_share_observations'], 1)
        self.assertEqual(n2['unresolved_share_observations'], 1)
        self.assertEqual(n1['verified_share_ids'], ['good'])
        self.assertEqual(n2['verified_share_ids'], [])
        self.assertEqual(result['verified_share_relationships'], 1)
        self.assertEqual(result['assessment'], 'INCOMPLETE')

    def test_nonobject_and_wrong_kind_accounted_without_invented_nas(self):
        data = topology()
        data['assets'].append({'id': 'h1', 'kind': 'host'})
        data['shares'] += [None, {'id': 'x', 'nas_id': 'h1', 'protocol': 'NFS'}]
        result = self.report(data)
        self.assertEqual(result['unresolved_share_observations'], 2)
        self.assertEqual(sum(a['unresolved_share_observations'] for a in result['assets']), 0)
        self.assertEqual(result['automatic_changes'], 0)

    def test_order_independent_read_only_and_windows_diagnostic_projection(self):
        data = topology()
        data['shares'] += [{'id': 'x', 'nas_id': 'n1', 'protocol': 'INVALID'}, None]
        original = copy.deepcopy(data)
        first = self.report(data)
        self.assertEqual(data, original)
        self.assertEqual(first, self.report(dict(data, shares=list(reversed(data['shares'])))))
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'topology.json'
            source.write_text(json.dumps(data), encoding='utf-8')
            report = assess_topology_file(source)
            self.assertEqual(report['dependency_impact']['unresolved_share_observations'], 2)
            display = format_risk_report(report)
            self.assertIn('Observations de partages sans relation résolue : 2', display)
            self.assertIn('partages_orphelins=1', display)


if __name__ == '__main__':
    unittest.main()
