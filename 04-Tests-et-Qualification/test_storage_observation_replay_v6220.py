"""V6.220 signed intra-snapshot replay quarantine; synthetic evidence only.
Author: Abdelhalim Talbi.
"""
import copy
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from storage_observation_auth_v6219 import sign_observation, find_replayed_observations
from storage_path_risk_v6194 import assess
from storage_dependency_impact_v6199 import map_dependencies

KEY = bytes(range(32))


def topology():
    path = {'host_id': 'h1', 'storage_id': 'a1', 'fabric': 'A', 'state': 'up',
            'source_ref': 'collector:approved', 'observed_at': '2026-10-24T10:00:00Z'}
    share = {'id': 's1', 'nas_id': 'n1', 'protocol': 'NFS', 'used_gib': 1,
             'quota_gib': 10, 'source_ref': 'collector:approved',
             'observed_at': '2026-10-24T10:00:00Z'}
    return {'schema': 'storagescope.storage-topology.v1',
            'observation_auth_policy': {'schema': 'storagescope.observation-auth-policy.v1',
                                        'source_keys': {'collector:approved': 'COLLECTOR_A'}},
            'assets': [{'id': 'h1', 'kind': 'host'},
                       {'id': 'a1', 'kind': 'storage_array', 'used_gib': 1, 'total_gib': 10},
                       {'id': 'n1', 'kind': 'nas', 'used_gib': 1, 'total_gib': 10}],
            'paths': [sign_observation(path, 'COLLECTOR_A', KEY)],
            'shares': [sign_observation(share, 'COLLECTOR_A', KEY)]}


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'STORAGESCOPE_HMAC_KEY_COLLECTOR_A': KEY.hex()})
        self.env.start()
        self.addCleanup(self.env.stop)

    def evaluate(self, data):
        risk = assess(data)
        return risk, map_dependencies(data, risk)

    def test_single_signed_observation_is_verified(self):
        risk, deps = self.evaluate(topology())
        self.assertEqual(risk['verified_active_paths'], 1)
        self.assertEqual(deps['verified_share_relationships'], 1)
        self.assertEqual(risk['replayed_path_observations'], 0)

    def test_repeated_signed_path_quarantines_both(self):
        data = topology()
        data['paths'].append(copy.deepcopy(data['paths'][0]))
        before = copy.deepcopy(data)
        risk, deps = self.evaluate(data)
        self.assertEqual(data, before)
        self.assertEqual(risk['verified_active_paths'], 0)
        self.assertEqual(deps['verified_host_relationships'], 0)
        self.assertEqual(deps['unverified_host_relationships'], 1)
        self.assertEqual(risk['replayed_path_observations'], 2)
        self.assertEqual(deps['replayed_path_observations'], 2)
        self.assertEqual(risk['assessment'], 'INCOMPLETE')
        self.assertEqual(sum(x['code'] == 'REPLAYED_PATH_OBSERVATION' for x in risk['findings']), 2)

    def test_repeated_signed_share_quarantines_both(self):
        data = topology()
        data['shares'].append(copy.deepcopy(data['shares'][0]))
        risk, deps = self.evaluate(data)
        self.assertEqual(risk['replayed_share_observations'], 2)
        self.assertEqual(deps['replayed_share_observations'], 2)
        self.assertEqual(deps['verified_share_relationships'], 0)
        self.assertEqual(deps['unresolved_share_observations'], 2)

    def test_distinct_signed_path_not_replay(self):
        data = topology()
        other = dict(data['paths'][0], fabric='B')
        data['paths'].append(sign_observation(other, 'COLLECTOR_A', KEY))
        risk, deps = self.evaluate(data)
        self.assertEqual(risk['replayed_path_observations'], 0)
        self.assertEqual(risk['verified_active_paths'], 2)
        self.assertEqual(deps['verified_host_relationships'], 1)

    def test_invalid_signature_not_counted_as_verified_replay(self):
        data = topology()
        data['paths'].append(dict(data['paths'][0], state='down'))
        risk, deps = self.evaluate(data)
        self.assertEqual(risk['replayed_path_observations'], 0)
        self.assertEqual(risk['verified_active_paths'], 0)
        self.assertEqual(deps['verified_host_relationships'], 0)

    def test_legacy_without_auth_policy_unchanged(self):
        data = topology()
        data.pop('observation_auth_policy')
        for record in data['paths'] + data['shares']:
            record.pop('auth')
        data['paths'].append(copy.deepcopy(data['paths'][0]))
        risk, _ = self.evaluate(data)
        self.assertEqual(risk['replayed_path_observations'], 0)
        self.assertEqual(risk['verified_active_paths'], 1)

    def test_scanner_returns_indices_only(self):
        data = topology()
        data['paths'].append(copy.deepcopy(data['paths'][0]))
        result = find_replayed_observations(
            data['paths'], data['shares'], {'collector:approved': 'COLLECTOR_A'})
        self.assertEqual(result, ({0, 1}, set()))
        self.assertNotIn(KEY.hex(), repr(result))


if __name__ == '__main__':
    unittest.main()
