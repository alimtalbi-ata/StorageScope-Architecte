"""V6.216 deterministic age-window quarantine, synthetic read-only fixtures.
Author: Abdelhalim Talbi.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from storage_observation_freshness_v6216 import load_policy, classify_observation
from storage_path_risk_v6194 import assess
from storage_dependency_impact_v6199 import map_dependencies
from storage_risk_desktop_v6196 import assess_topology_file, format_risk_report, export_risk_report


def topology():
    return {'schema': 'storagescope.storage-topology.v1',
            'freshness_policy': {'schema': 'storagescope.observation-freshness-policy.v1',
                                 'reference_time': '2026-10-24T12:00:00+02:00',
                                 'max_age_seconds': 120, 'max_future_skew_seconds': 5},
            'assets': [{'id': 'h1', 'kind': 'host'},
                       {'id': 'a1', 'kind': 'storage_array', 'used_gib': 20, 'total_gib': 100},
                       {'id': 'n1', 'kind': 'nas', 'used_gib': 20, 'total_gib': 100}],
            'paths': [{'host_id': 'h1', 'storage_id': 'a1', 'fabric': 'A', 'port': 'p1',
                       'state': 'up', 'observed_at': '2026-10-24T09:59:00Z'}],
            'shares': [{'id': 's1', 'nas_id': 'n1', 'protocol': 'NFS',
                        'used_gib': 1, 'quota_gib': 10, 'observed_at': '2026-10-24T10:00:00Z'}]}


def reviewed(data):
    risk = assess(data)
    return risk, map_dependencies(data, risk)


class FreshnessTests(unittest.TestCase):
    def test_fresh_observations_and_unauthenticated_reference(self):
        risk, dep = reviewed(topology())
        self.assertEqual(risk['verified_active_paths'], 1)
        self.assertEqual(dep['verified_host_relationships'], 1)
        self.assertEqual(dep['verified_share_relationships'], 1)
        self.assertEqual(dep['freshness_evaluation']['fresh_observations'], 2)
        self.assertEqual(dep['freshness_evaluation']['reference_time'], '2026-10-24T10:00:00Z')
        self.assertEqual(dep['freshness_evaluation']['trust'], 'UNAUTHENTICATED_INPUT_CLOCK')
        self.assertEqual(dep['automatic_changes'], 0)

    def test_stale_path_poison_is_order_independent(self):
        data = topology()
        stale = dict(data['paths'][0], observed_at='2026-10-24T09:57:59Z')
        for items in ([data['paths'][0], stale], [stale, data['paths'][0]]):
            sample = dict(data, paths=items)
            risk, dep = reviewed(sample)
            self.assertEqual(risk['verified_active_paths'], 0)
            self.assertEqual(dep['verified_host_relationships'], 0)
            self.assertEqual(dep['unverified_host_relationships'], 1)
            self.assertEqual(dep['assessment'], 'INCOMPLETE')
            self.assertIn('PATH_STALE_OBSERVATION', [x['code'] for x in risk['findings']])

    def test_future_path_and_share_are_quarantined(self):
        data = topology()
        data['paths'][0]['observed_at'] = '2026-10-24T10:00:06Z'
        data['shares'][0]['observed_at'] = '2026-10-24T10:00:06Z'
        risk, dep = reviewed(data)
        self.assertEqual(risk['verified_active_paths'], 0)
        self.assertEqual(dep['verified_host_relationships'], 0)
        self.assertEqual(dep['verified_share_relationships'], 0)
        self.assertEqual(dep['freshness_evaluation']['future_observations'], 2)
        self.assertIn('PATH_FUTURE_OBSERVATION', [x['code'] for x in risk['findings']])
        self.assertIn('SHARE_FUTURE_OBSERVATION', [x['code'] for x in risk['findings']])

    def test_missing_timestamp_under_policy_is_not_trusted(self):
        data = topology()
        del data['paths'][0]['observed_at']
        del data['shares'][0]['observed_at']
        risk, dep = reviewed(data)
        self.assertEqual(risk['verified_active_paths'], 0)
        self.assertEqual(dep['verified_host_relationships'], 0)
        self.assertEqual(dep['verified_share_relationships'], 0)
        self.assertEqual(dep['freshness_evaluation']['missing_observations'], 2)

    def test_policy_boundaries_and_future_skew(self):
        policy = load_policy(topology())
        for timestamp in ('2026-10-24T09:58:00Z', '2026-10-24T10:00:05Z'):
            self.assertEqual(classify_observation({'observed_at': timestamp}, policy), 'FRESH')
        self.assertEqual(classify_observation({'observed_at': '2026-10-24T09:57:59.999999Z'}, policy), 'STALE')
        self.assertEqual(classify_observation({'observed_at': '2026-10-24T10:00:05.000001Z'}, policy), 'FUTURE')

    def test_reject_invalid_policy_and_boolean_thresholds(self):
        for field, value in [('max_age_seconds', True), ('max_age_seconds', 0),
                             ('max_age_seconds', 31_536_001), ('max_future_skew_seconds', -1),
                             ('max_future_skew_seconds', 3601), ('reference_time', '2026-10-24T10:00:00')]:
            data = topology()
            data['freshness_policy'][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                reviewed(data)
        data = topology()
        data['freshness_policy']['trust_me'] = True
        with self.assertRaises(ValueError):
            reviewed(data)

    def test_legacy_snapshots_remain_compatible_without_claiming_freshness(self):
        data = topology()
        del data['freshness_policy']
        del data['paths'][0]['observed_at']
        risk, dep = reviewed(data)
        self.assertEqual(risk['verified_active_paths'], 1)
        self.assertEqual(dep['verified_host_relationships'], 1)
        self.assertIsNone(dep['freshness_evaluation'])
        self.assertEqual(dep['observation_times']['freshness'], 'NOT_ASSESSED')

    def test_independent_fabric_remains_but_mixed_evidence_is_incomplete(self):
        data = topology()
        data['paths'].append(dict(data['paths'][0], fabric='B', port='p2',
                                  observed_at='2026-10-24T09:57:59Z'))
        risk, dep = reviewed(data)
        self.assertEqual(risk['verified_active_paths'], 1)
        self.assertEqual(dep['verified_host_relationships'], 1)
        self.assertEqual(dep['unverified_host_relationships'], 1)
        self.assertEqual(dep['mixed_evidence_host_relationships'], 1)
        self.assertEqual(dep['assessment'], 'INCOMPLETE')

    def test_desktop_export_is_deterministic_and_read_only(self):
        data = topology()
        data['shares'][0]['observed_at'] = '2026-10-24T09:00:00Z'
        original = copy.deepcopy(data)
        with tempfile.TemporaryDirectory() as tmp:
            source, dest = Path(tmp)/'topology.json', Path(tmp)/'report.json'
            source.write_text(json.dumps(data), encoding='utf-8')
            report = assess_topology_file(source)
            self.assertIn('Observations périmées : 1', format_risk_report(report))
            self.assertIn('NON AUTHENTIFIÉES', format_risk_report(report))
            export_risk_report(source, dest)
            self.assertEqual(json.loads(dest.read_text(encoding='utf-8')), report)
        self.assertEqual(data, original)


if __name__ == '__main__':
    unittest.main()
