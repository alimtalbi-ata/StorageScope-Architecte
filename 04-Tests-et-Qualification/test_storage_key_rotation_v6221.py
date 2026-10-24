"""V6.221 bounded HMAC key rotation; synthetic offline regression tests.
Author: Abdelhalim Talbi.
"""
import copy
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from storage_observation_auth_v6219 import (
    classify_auth, find_replayed_observations, load_auth_policy, sign_observation,
)
from storage_path_risk_v6194 import assess
from storage_dependency_impact_v6199 import map_dependencies

OLD = bytes(range(32))
NEW = bytes(range(32, 64))


def topology():
    path = {'host_id': 'host1', 'storage_id': 'array1', 'fabric': 'A',
            'state': 'up', 'source_ref': 'collector:approved'}
    share = {'id': 'share1', 'nas_id': 'nas1', 'protocol': 'NFS',
             'used_gib': 1, 'quota_gib': 10, 'source_ref': 'collector:approved'}
    return {'schema': 'storagescope.storage-topology.v1',
            'observation_auth_policy': {
                'schema': 'storagescope.observation-auth-policy.v2',
                'source_keys': {'collector:approved': ['NEW_KEY', 'OLD_KEY']}},
            'assets': [{'id': 'host1', 'kind': 'host'},
                       {'id': 'array1', 'kind': 'storage_array',
                        'used_gib': 10, 'total_gib': 100},
                       {'id': 'nas1', 'kind': 'nas', 'used_gib': 1, 'total_gib': 10}],
            'paths': [sign_observation(path, 'OLD_KEY', OLD)],
            'shares': [sign_observation(share, 'NEW_KEY', NEW)]}


class KeyRotationTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {
            'STORAGESCOPE_HMAC_KEY_OLD_KEY': OLD.hex(),
            'STORAGESCOPE_HMAC_KEY_NEW_KEY': NEW.hex()})
        env.start()
        self.addCleanup(env.stop)

    def test_both_keys_verified_during_rotation(self):
        data = topology()
        before = copy.deepcopy(data)
        risk = assess(data)
        deps = map_dependencies(data, risk)
        self.assertEqual(data, before)
        self.assertEqual(risk['verified_active_paths'], 1)
        self.assertEqual(deps['verified_share_relationships'], 1)
        self.assertEqual(risk['observation_authentication']['verified_observations'], 2)
        self.assertEqual(risk['observation_authentication']['rotation_active_sources'], 1)
        self.assertEqual(risk['automatic_changes'], 0)

    def test_retired_old_key_is_quarantined_even_if_secret_remains(self):
        data = topology()
        data['observation_auth_policy']['source_keys']['collector:approved'] = ['NEW_KEY']
        risk = assess(data)
        deps = map_dependencies(data, risk)
        self.assertEqual(risk['verified_active_paths'], 0)
        self.assertEqual(deps['verified_host_relationships'], 0)
        self.assertEqual(deps['verified_share_relationships'], 1)
        self.assertEqual(risk['observation_authentication']['invalid_auth_observations'], 1)
        self.assertEqual(risk['observation_authentication']['rotation_active_sources'], 0)

    def test_missing_new_secret_fails_closed(self):
        with patch.dict(os.environ, {'STORAGESCOPE_HMAC_KEY_NEW_KEY': ''}):
            risk = assess(topology())
        self.assertEqual(risk['observation_authentication']['key_unavailable_observations'], 1)
        self.assertNotIn(NEW.hex(), repr(risk))

    def test_tampered_new_key_signature_fails_closed(self):
        data = topology()
        data['shares'][0]['quota_gib'] = 100
        risk = assess(data)
        self.assertEqual(risk['observation_authentication']['bad_signature_observations'], 1)
        self.assertIn('UNAUTHENTICATED_SHARE_OBSERVATION',
                      {f['code'] for f in risk['findings']})

    def test_cross_source_key_reuse_rejected(self):
        data = topology()
        data['observation_auth_policy']['source_keys']['collector:other'] = ['OLD_KEY']
        with self.assertRaises(ValueError):
            assess(data)

    def test_duplicate_rotation_key_rejected(self):
        data = topology()
        data['observation_auth_policy']['source_keys']['collector:approved'] = ['NEW_KEY', 'NEW_KEY']
        with self.assertRaises(ValueError):
            assess(data)

    def test_empty_three_key_and_malformed_windows_rejected(self):
        for ids in ([], ['A', 'B', 'C'], 'NEW_KEY', [42], ['bad-key']):
            with self.subTest(ids=ids):
                data = topology()
                data['observation_auth_policy']['source_keys']['collector:approved'] = ids
                with self.assertRaises(ValueError):
                    assess(data)

    def test_v1_remains_compatible(self):
        data = topology()
        data['observation_auth_policy'] = {
            'schema': 'storagescope.observation-auth-policy.v1',
            'source_keys': {'collector:approved': 'OLD_KEY'}}
        policy = load_auth_policy(data)
        self.assertEqual(classify_auth(data['paths'][0], policy), 'VERIFIED')
        self.assertEqual(classify_auth(data['shares'][0], policy), 'INVALID_AUTH')

    def test_operator_v2_pin_blocks_downgrade(self):
        data = topology()
        with patch.dict(os.environ, {'STORAGESCOPE_REQUIRE_OBSERVATION_AUTH_V2': '1'}):
            self.assertIsNotNone(load_auth_policy(data))
            data['observation_auth_policy'] = {
                'schema': 'storagescope.observation-auth-policy.v1',
                'source_keys': {'collector:approved': 'OLD_KEY'}}
            with self.assertRaises(ValueError):
                assess(data)
            data.pop('observation_auth_policy')
            with self.assertRaises(ValueError):
                assess(data)

    def test_replay_scanner_works_with_rotation(self):
        data = topology()
        data['paths'].append(copy.deepcopy(data['paths'][0]))
        self.assertEqual(find_replayed_observations(
            data['paths'], data['shares'], load_auth_policy(data)), ({0, 1}, set()))
        self.assertEqual(assess(data)['replayed_path_observations'], 2)

    def test_policy_rejects_extra_fields(self):
        data = topology()
        data['observation_auth_policy']['not_allowed'] = True
        with self.assertRaises(ValueError):
            assess(data)

    def test_no_key_identifiers_or_secrets_in_summary(self):
        summary = repr(assess(topology())['observation_authentication'])
        for forbidden in ('OLD_KEY', 'NEW_KEY', OLD.hex(), NEW.hex()):
            self.assertNotIn(forbidden, summary)


if __name__ == '__main__':
    unittest.main()
