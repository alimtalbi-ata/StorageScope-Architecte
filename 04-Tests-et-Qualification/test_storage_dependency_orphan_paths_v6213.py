"""V6.213: unresolved SAN path evidence remains attributable, fail-closed.
Synthetic read-only fixtures. Author: Abdelhalim Talbi.
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
                   {'id': 'a1', 'kind': 'storage_array', 'used_gib': 20, 'total_gib': 100},
                   {'id': 'a2', 'kind': 'storage_array', 'used_gib': 10, 'total_gib': 100}],
        'paths': [{'host_id': 'h1', 'storage_id': 'a1', 'fabric': 'A', 'state': 'up'}],
        'shares': [],
    }


class OrphanPathEvidenceTests(unittest.TestCase):
    def report(self, data):
        return map_dependencies(data, assess(data))

    def test_unknown_host_attributed_to_known_array_not_verified(self):
        data = topology()
        data['paths'].append({'host_id': 'missing-host', 'storage_id': 'a1', 'fabric': 'B', 'state': 'up'})
        result = self.report(data)
        array = next(a for a in result['assets'] if a['asset_id'] == 'a1')
        self.assertEqual(array['verified_host_ids'], ['h1'])
        self.assertEqual(array['unverified_host_ids'], [])
        self.assertEqual(array['unresolved_path_observations'], 1)
        self.assertEqual(result['unresolved_path_observations'], 1)
        self.assertEqual(result['assessment'], 'INCOMPLETE')
        self.assertEqual(result['automatic_changes'], 0)

    def test_missing_host_and_wrong_kind_not_promoted(self):
        data = topology()
        data['paths'] += [
            {'storage_id': 'a1', 'fabric': 'B', 'state': 'up'},
            {'host_id': 'a2', 'storage_id': 'a1', 'fabric': 'C', 'state': 'up'},
        ]
        result = self.report(data)
        array = next(a for a in result['assets'] if a['asset_id'] == 'a1')
        self.assertEqual(array['unresolved_path_observations'], 2)
        self.assertEqual(result['unresolved_path_observations'], 2)
        self.assertEqual(result['verified_host_relationships'], 1)

    def test_unknown_array_and_nonobject_globally_accounted(self):
        data = topology()
        data['paths'] += [{'host_id': 'h1', 'storage_id': 'missing-array', 'fabric': 'B', 'state': 'up'}, None]
        result = self.report(data)
        self.assertEqual(result['unresolved_path_observations'], 2)
        self.assertEqual(sum(a['unresolved_path_observations'] for a in result['assets']), 0)
        self.assertEqual(result['assessment'], 'INCOMPLETE')

    def test_order_independent_no_mutation_isolated_array(self):
        data = topology()
        data['paths'].append({'host_id': 'missing-host', 'storage_id': 'a1', 'fabric': 'B', 'state': 'up'})
        original = copy.deepcopy(data)
        first = self.report(data)
        self.assertEqual(data, original)
        self.assertEqual(first, self.report(dict(data, paths=list(reversed(data['paths'])))))
        a2 = next(a for a in first['assets'] if a['asset_id'] == 'a2')
        self.assertEqual(a2['unresolved_path_observations'], 0)

    def test_windows_diagnostic_projection_exposes_orphans(self):
        data = topology()
        data['paths'].append({'host_id': 'missing-host', 'storage_id': 'a1', 'fabric': 'B', 'state': 'up'})
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'topology.json'
            source.write_text(json.dumps(data), encoding='utf-8')
            report = assess_topology_file(source)
            self.assertEqual(report['dependency_impact']['unresolved_path_observations'], 1)
            display = format_risk_report(report)
            self.assertIn('Observations de chemins sans relation résolue : 1', display)
            self.assertIn('chemins_orphelins=1', display)


if __name__ == '__main__':
    unittest.main()
