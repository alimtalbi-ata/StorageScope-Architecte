"""V6.215: timezone provenance is explicit and bad timestamps fail closed.

Synthetic read-only SAN/NAS fixtures. Author: Abdelhalim Talbi.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from storage_observation_time_v6215 import parse_observed_at, summarize_observation_times
from storage_path_risk_v6194 import assess
from storage_dependency_impact_v6199 import map_dependencies
from storage_risk_desktop_v6196 import assess_topology_file, format_risk_report, export_risk_report


def topology():
    return {
        'schema': 'storagescope.storage-topology.v1',
        'assets': [
            {'id': 'h1', 'kind': 'host'},
            {'id': 'a1', 'kind': 'storage_array', 'used_gib': 20, 'total_gib': 100},
            {'id': 'n1', 'kind': 'nas', 'used_gib': 20, 'total_gib': 100},
        ],
        'paths': [{'host_id': 'h1', 'storage_id': 'a1', 'fabric': 'A',
                   'state': 'up', 'observed_at': '2026-10-24T12:00:00+02:00'}],
        'shares': [{'id': 's1', 'nas_id': 'n1', 'protocol': 'NFS',
                    'used_gib': 1, 'quota_gib': 10,
                    'observed_at': '2026-10-24T10:00:01Z'}],
    }


class ObservationTimestampTests(unittest.TestCase):
    def test_timezone_offsets_normalize_to_utc(self):
        self.assertEqual(parse_observed_at({'observed_at': '2026-10-24T12:00:00+02:00'}),
                         ('VALID', '2026-10-24T10:00:00Z'))
        self.assertEqual(parse_observed_at({'observed_at': '2026-10-24T09:30:00-00:30'}),
                         ('VALID', '2026-10-24T10:00:00Z'))
        self.assertEqual(parse_observed_at({'observed_at': '2026-10-24T10:00:00.123456Z'}),
                         ('VALID', '2026-10-24T10:00:00.123456Z'))

    def test_reject_naive_invalid_and_non_string_times(self):
        for value in ('2026-10-24T12:00:00', '2026-02-30T12:00:00Z',
                      '2026-10-24', ' 2026-10-24T12:00:00Z',
                      '2026-10-24T12:00:00.1234567Z', None, True, 123):
            with self.subTest(value=value):
                self.assertEqual(parse_observed_at({'observed_at': value}), ('INVALID', None))
        self.assertEqual(parse_observed_at({}), ('MISSING', None))
        self.assertEqual(parse_observed_at(None), ('MISSING', None))

    def test_timestamp_summary_is_order_independent_and_never_claims_freshness(self):
        data = topology()
        data['paths'].append({'observed_at': 'invalid'})
        summary = summarize_observation_times(data['paths'], data['shares'])
        self.assertEqual(summary['valid_observations'], 2)
        self.assertEqual(summary['invalid_observations'], 1)
        self.assertEqual(summary['latest_parsed_utc'], '2026-10-24T10:00:01Z')
        self.assertEqual(summary['freshness'], 'NOT_ASSESSED')
        self.assertEqual(summary, summarize_observation_times(
            list(reversed(data['paths'])), list(reversed(data['shares']))))

    def test_valid_time_does_not_create_service_impact_or_freshness_claim(self):
        data = topology()
        result = map_dependencies(data, assess(data))
        self.assertEqual(result['verified_host_relationships'], 1)
        self.assertEqual(result['verified_share_relationships'], 1)
        self.assertEqual(result['observation_times']['valid_observations'], 2)
        self.assertEqual(result['observation_times']['missing_observations'], 0)
        self.assertEqual(result['automatic_changes'], 0)
        self.assertEqual(result['assessment'], 'OBSERVED_DEPENDENCIES_ONLY')

    def test_invalid_time_poison_same_san_signature_in_both_orders(self):
        data = topology()
        bad = dict(data['paths'][0], observed_at='2026-10-24T12:00:00')
        for paths in ([data['paths'][0], bad], [bad, data['paths'][0]]):
            with self.subTest(paths=paths):
                sample = dict(data, paths=paths)
                risk = assess(sample)
                dep = map_dependencies(sample, risk)
                self.assertEqual(risk['verified_active_paths'], 0)
                self.assertIn('INVALID_PATH_TIMESTAMP', [f['code'] for f in risk['findings']])
                self.assertEqual(dep['verified_host_relationships'], 0)
                self.assertEqual(dep['unverified_host_relationships'], 1)
                self.assertEqual(dep['unresolved_path_observations'], 1)
                self.assertEqual(dep['assets'][0]['unresolved_path_observations'], 1)
                self.assertEqual(dep['observation_times']['invalid_observations'], 1)
                self.assertEqual(dep['assessment'], 'INCOMPLETE')

    def test_bad_time_on_one_fabric_does_not_hide_independent_good_fabric(self):
        data = topology()
        data['paths'].append(dict(data['paths'][0], fabric='B', observed_at='bad'))
        dep = map_dependencies(data, assess(data))
        self.assertEqual(dep['verified_host_relationships'], 1)
        self.assertEqual(dep['unverified_host_relationships'], 1)
        self.assertEqual(dep['mixed_evidence_host_relationships'], 1)
        self.assertEqual(dep['assessment'], 'INCOMPLETE')

    def test_invalid_share_timestamp_is_quarantined_without_hiding_good_share(self):
        data = topology()
        data['shares'].append({'id': 'bad', 'nas_id': 'n1', 'protocol': 'SMB',
                               'used_gib': 1, 'quota_gib': 10,
                               'observed_at': 'not-a-time'})
        risk = assess(data)
        dep = map_dependencies(data, risk)
        self.assertIn('INVALID_SHARE_TIMESTAMP', [f['code'] for f in risk['findings']])
        self.assertEqual(dep['verified_share_relationships'], 1)
        self.assertEqual(dep['unresolved_share_observations'], 1)
        self.assertEqual(dep['assets'][1]['verified_share_ids'], ['s1'])
        self.assertEqual(dep['assets'][1]['unresolved_share_observations'], 1)
        self.assertEqual(dep['assessment'], 'INCOMPLETE')

    def test_legacy_missing_times_remain_observed_but_not_freshness_verified(self):
        data = topology()
        del data['paths'][0]['observed_at']
        del data['shares'][0]['observed_at']
        dep = map_dependencies(data, assess(data))
        self.assertEqual(dep['verified_host_relationships'], 1)
        self.assertEqual(dep['verified_share_relationships'], 1)
        self.assertEqual(dep['observation_times']['missing_observations'], 2)
        self.assertIsNone(dep['observation_times']['latest_parsed_utc'])
        self.assertEqual(dep['observation_times']['freshness'], 'NOT_ASSESSED')

    def test_read_only_determinism_diagnostics_and_export(self):
        data = topology()
        data['paths'].append(dict(data['paths'][0], observed_at='bad'))
        original = copy.deepcopy(data)
        self.assertEqual(map_dependencies(data, assess(data)),
                         map_dependencies(data, assess(data)))
        self.assertEqual(data, original)
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / 'input.json', Path(tmp) / 'report.json'
            source.write_text(json.dumps(data), encoding='utf-8')
            report = assess_topology_file(source)
            screen = format_risk_report(report)
            self.assertIn('Horodatages invalides : 1', screen)
            self.assertIn('Fraîcheur : NON ÉVALUÉE', screen)
            export_risk_report(source, output)
            self.assertEqual(json.loads(output.read_text(encoding='utf-8'))
                             ['dependency_impact']['observation_times'],
                             report['dependency_impact']['observation_times'])


if __name__ == '__main__':
    unittest.main()
