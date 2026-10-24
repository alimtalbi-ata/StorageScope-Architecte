"""V6.211: mixed SAN path evidence remains visible with a healthy alternate path.

Synthetic read-only fixtures. Author: Abdelhalim Talbi.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / '03-Sources'
sys.path.insert(0, str(SOURCE))
from storage_path_risk_v6194 import assess
from storage_dependency_impact_v6199 import map_dependencies
from storage_risk_desktop_v6196 import assess_topology_file, format_risk_report


def topology():
    return {
        'schema': 'storagescope.storage-topology.v1',
        'assets': [{'id': 'h1', 'kind': 'host'},
                   {'id': 'a1', 'kind': 'storage_array', 'used_gib': 20, 'total_gib': 100},
                   {'id': 'n1', 'kind': 'nas', 'used_gib': 20, 'total_gib': 100}],
        'paths': [
            {'host_id': 'h1', 'storage_id': 'a1', 'fabric': 'A', 'port': 'p1', 'state': 'up'},
            {'host_id': 'h1', 'storage_id': 'a1', 'fabric': 'A', 'port': 'p1', 'state': 'down'},
            {'host_id': 'h1', 'storage_id': 'a1', 'fabric': 'B', 'port': 'p2', 'state': 'up'},
        ],
        'shares': [{'id': 's1', 'nas_id': 'n1', 'protocol': 'NFS', 'used_gib': 1, 'quota_gib': 10}],
    }


class MixedEvidenceTests(unittest.TestCase):
    def report(self, data):
        return map_dependencies(data, assess(data))

    def test_conflicting_path_not_hidden_by_other_verified_fabric(self):
        report = self.report(topology())
        array = next(a for a in report['assets'] if a['asset_id'] == 'a1')
        self.assertEqual(array['verified_host_ids'], ['h1'])
        self.assertEqual(array['unverified_host_ids'], ['h1'])
        self.assertEqual(array['mixed_evidence_host_ids'], ['h1'])
        self.assertEqual(report['verified_host_relationships'], 1)
        self.assertEqual(report['unverified_host_relationships'], 1)
        self.assertEqual(report['mixed_evidence_host_relationships'], 1)
        self.assertEqual(report['assessment'], 'INCOMPLETE')
        self.assertEqual(report['automatic_changes'], 0)

    def test_independent_verified_pair_stays_healthy(self):
        data = topology()
        data['assets'] += [{'id': 'h2', 'kind': 'host'},
                           {'id': 'a2', 'kind': 'storage_array', 'used_gib': 1, 'total_gib': 10}]
        data['paths'].append({'host_id': 'h2', 'storage_id': 'a2', 'fabric': 'C', 'state': 'up'})
        report = self.report(data)
        a2 = next(a for a in report['assets'] if a['asset_id'] == 'a2')
        self.assertEqual(a2['verified_host_ids'], ['h2'])
        self.assertEqual(a2['unverified_host_ids'], [])
        self.assertEqual(a2['mixed_evidence_host_ids'], [])
        self.assertEqual(report['mixed_evidence_host_relationships'], 1)

    def test_unknown_alternate_path_still_requires_review(self):
        data = topology()
        data['paths'] = [data['paths'][2], dict(data['paths'][0], state='unknown')]
        report = self.report(data)
        self.assertEqual(report['unverified_host_relationships'], 1)
        self.assertEqual(report['mixed_evidence_host_relationships'], 1)
        self.assertEqual(report['assessment'], 'INCOMPLETE')

    def test_order_independent_and_no_mutation(self):
        data = topology()
        before = copy.deepcopy(data)
        report = self.report(data)
        data['paths'].reverse()
        self.assertEqual(report, self.report(data))
        self.assertEqual(before['paths'], list(reversed(data['paths'])))

    def test_desktop_shows_mixed_path_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'topology.json'
            source.write_text(json.dumps(topology()), encoding='utf-8')
            report = assess_topology_file(source)
            self.assertEqual(report['dependency_impact']['mixed_evidence_host_relationships'], 1)
            display = format_risk_report(report)
            self.assertIn('Relations hôtes non vérifiées : 1', display)
            self.assertIn('Relations hôtes à preuves mixtes : 1', display)


if __name__ == '__main__':
    unittest.main()
