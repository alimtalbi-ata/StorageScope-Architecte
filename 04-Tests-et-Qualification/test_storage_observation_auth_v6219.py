"""V6.219 offline HMAC authentication; synthetic observations only.
Author: Abdelhalim Talbi.
"""
import copy
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

SRC = pathlib.Path(__file__).resolve().parents[1] / '03-Sources'
sys.path.insert(0, str(SRC))
from storage_observation_auth_v6219 import (
    load_auth_policy, classify_auth, sign_observation, summarize_auth,
)
from storage_path_risk_v6194 import assess
from storage_dependency_impact_v6199 import map_dependencies
from storage_risk_desktop_v6196 import assess_topology_file, format_risk_report

KEY = bytes(range(32))
KEY_ENV = 'STORAGESCOPE_HMAC_KEY_COLLECTOR_A'


def topology():
    return {
        'schema': 'storagescope.storage-topology.v1',
        'source_policy': {'schema': 'storagescope.observation-source-policy.v1',
                          'allowed_source_refs': ['collector:approved']},
        'observation_auth_policy': {'schema': 'storagescope.observation-auth-policy.v1',
                                    'source_keys': {'collector:approved': 'COLLECTOR_A'}},
        'assets': [{'id': 'h1', 'kind': 'host'},
                   {'id': 'a1', 'kind': 'storage_array', 'used_gib': 10, 'total_gib': 100},
                   {'id': 'n1', 'kind': 'nas', 'used_gib': 10, 'total_gib': 100}],
        'paths': [{'host_id': 'h1', 'storage_id': 'a1', 'fabric': 'A',
                   'state': 'up', 'source_ref': 'collector:approved',
                   'observed_at': '2026-10-24T11:00:00+00:00'}],
        'shares': [{'id': 's1', 'nas_id': 'n1', 'protocol': 'NFS',
                    'used_gib': 1, 'quota_gib': 10,
                    'source_ref': 'collector:approved',
                    'observed_at': '2026-10-24T11:00:00+00:00'}],
    }


def signed():
    data = topology()
    for name in ('paths', 'shares'):
        data[name] = [sign_observation(item, 'COLLECTOR_A', KEY)
                      for item in data[name]]
    return data


def evaluate(data):
    risk = assess(data)
    return risk, map_dependencies(data, risk)


class ObservationAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {KEY_ENV: KEY.hex()})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_signed_path_and_share_are_verified(self):
        data = signed()
        before = copy.deepcopy(data)
        risk, deps = evaluate(data)
        self.assertEqual(data, before)
        self.assertEqual(risk['verified_active_paths'], 1)
        self.assertEqual(deps['verified_share_relationships'], 1)
        self.assertEqual(risk['observation_authentication']['verified_observations'], 2)
        self.assertEqual(deps['observation_authentication']['verified_observations'], 2)
        self.assertEqual(deps['observation_authentication']['authentication'],
                         'SHARED_KEY_HMAC_VERIFIED_ONLY')
        self.assertEqual(risk['automatic_changes'], 0)
        self.assertEqual(deps['automatic_changes'], 0)

    def test_tampered_active_path_is_quarantined(self):
        data = signed()
        data['paths'][0]['state'] = 'down'
        risk, deps = evaluate(data)
        self.assertEqual(risk['verified_active_paths'], 0)
        self.assertEqual(deps['verified_host_relationships'], 0)
        self.assertEqual(deps['unverified_host_relationships'], 1)
        self.assertEqual(risk['assessment'], 'INCOMPLETE')
        self.assertIn('UNAUTHENTICATED_PATH_OBSERVATION',
                      {item['code'] for item in risk['findings']})
        self.assertEqual(deps['observation_authentication']['bad_signature_observations'], 1)

    def test_tampered_share_quota_is_quarantined(self):
        data = signed()
        data['shares'][0]['quota_gib'] = 100
        risk, deps = evaluate(data)
        self.assertEqual(deps['verified_share_relationships'], 0)
        self.assertEqual(deps['unresolved_share_observations'], 1)
        self.assertIn('UNAUTHENTICATED_SHARE_OBSERVATION',
                      {item['code'] for item in risk['findings']})

    def test_invalid_duplicate_poison_is_order_independent(self):
        data = signed()
        invalid = copy.deepcopy(data['paths'][0])
        invalid['state'] = 'down'
        for paths in ([data['paths'][0], invalid], [invalid, data['paths'][0]]):
            item = copy.deepcopy(data)
            item['paths'] = copy.deepcopy(paths)
            risk, deps = evaluate(item)
            self.assertEqual(risk['verified_active_paths'], 0)
            self.assertEqual(deps['verified_host_relationships'], 0)
            self.assertEqual(deps['unverified_host_relationships'], 1)

    def test_missing_key_quarantines_without_disclosing_secrets(self):
        data = signed()
        with patch.dict(os.environ, {KEY_ENV: ''}):
            risk, deps = evaluate(data)
        self.assertEqual(risk['verified_active_paths'], 0)
        self.assertEqual(deps['verified_share_relationships'], 0)
        self.assertEqual(risk['observation_authentication']['key_unavailable_observations'], 2)
        self.assertNotIn(KEY.hex(), repr(risk) + repr(deps))
        self.assertNotIn('COLLECTOR_A', repr(risk) + repr(deps))

    def test_missing_or_unknown_source_and_bad_envelope_fail_closed(self):
        policy = load_auth_policy(signed())
        record = signed()['paths'][0]
        cases = [({}, 'MISSING_SOURCE'),
                 ({**record, 'source_ref': 'other'}, 'UNKNOWN_SOURCE'),
                 ({key: val for key, val in record.items() if key != 'auth'}, 'MISSING_AUTH'),
                 ({**record, 'auth': {'key_id': 'COLLECTOR_B', 'hmac_sha256': '0' * 64}}, 'INVALID_AUTH'),
                 ({**record, 'auth': {'key_id': 'COLLECTOR_A', 'hmac_sha256': '0' * 64, 'extra': 1}}, 'INVALID_AUTH')]
        for sample, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(classify_auth(sample, policy), expected)

    def test_policy_rejects_unknown_fields_duplicate_key_reuse_and_bad_ids(self):
        for keys in ({}, {'ok': 'collector-key'}, {'ok': 'COLLECTOR_A', 'other': 'COLLECTOR_A'},
                     {'not valid': 'COLLECTOR_A'}, {'ok': 123},
                     {str(i): 'K' + str(i) for i in range(65)}):
            data = topology()
            data['observation_auth_policy']['source_keys'] = keys
            with self.subTest(keys=str(keys)[:30]), self.assertRaises(ValueError):
                assess(data)
        data = topology()
        data['observation_auth_policy']['trust_me'] = True
        with self.assertRaises(ValueError):
            assess(data)

    def test_operator_enforcement_blocks_policy_stripping_downgrade(self):
        data = signed()
        data.pop('observation_auth_policy')
        with patch.dict(os.environ, {'STORAGESCOPE_REQUIRE_OBSERVATION_AUTH': '1'}):
            with self.assertRaisesRegex(ValueError, 'required by operator'):
                evaluate(data)
        with patch.dict(os.environ, {'STORAGESCOPE_REQUIRE_OBSERVATION_AUTH': 'invalid'}):
            with self.assertRaisesRegex(ValueError, 'enforcement setting'):
                evaluate(data)

    def test_legacy_without_auth_policy_is_unchanged(self):
        data = topology()
        data.pop('observation_auth_policy')
        risk, deps = evaluate(data)
        self.assertEqual(risk['verified_active_paths'], 1)
        self.assertEqual(deps['verified_share_relationships'], 1)
        self.assertIsNone(risk['observation_authentication'])
        self.assertIsNone(deps['observation_authentication'])

    def test_signature_binds_source_timestamp_and_unicode_payload(self):
        data = signed()
        original = data['paths'][0]
        for field, value in (('source_ref', 'collector:unlisted'),
                             ('observed_at', '2026-10-24T11:01:00+00:00'),
                             ('note', 'Équipement SAN')):
            tampered = copy.deepcopy(original)
            tampered[field] = value
            self.assertNotEqual(classify_auth(tampered, load_auth_policy(data)), 'VERIFIED')
        sample = {'source_ref': 'collector:approved', 'note': 'Équipement SAN'}
        signed_sample = sign_observation(sample, 'COLLECTOR_A', KEY)
        self.assertEqual(classify_auth(signed_sample, load_auth_policy(data)), 'VERIFIED')

    def test_authentication_does_not_override_staleness(self):
        data = signed()
        data['freshness_policy'] = {'schema': 'storagescope.observation-freshness-policy.v1',
                                    'reference_time': '2026-10-24T14:00:00Z',
                                    'max_age_seconds': 60, 'max_future_skew_seconds': 0}
        # If schema changes, the existing strict freshness parser will fail fast.
        try:
            risk, deps = evaluate(data)
        except ValueError as exc:
            self.fail(f'Synthetic freshness fixture rejected: {exc}')
        self.assertEqual(risk['verified_active_paths'], 0)
        self.assertEqual(deps['verified_share_relationships'], 0)

    def test_file_round_trip_and_windows_diagnostic_disclaimer(self):
        data = signed()
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / 'signed.json'
            path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
            report = assess_topology_file(path)
        text = format_risk_report(report)
        self.assertIn('Observations HMAC vérifiées : 2', text)
        self.assertIn('identité indépendante et horloge NON ATTESTÉES', text)
        self.assertNotIn(KEY.hex(), text)

    def test_signature_rejects_nonfinite_payload_and_short_keys(self):
        policy = load_auth_policy(signed())
        sample = signed()['paths'][0]
        bad = {**sample, 'state': float('nan')}
        self.assertEqual(classify_auth(bad, policy), 'INVALID_PAYLOAD')
        with self.assertRaises(ValueError):
            sign_observation(sample, 'COLLECTOR_A', b'short')


if __name__ == '__main__':
    unittest.main()
