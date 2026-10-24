"""V6.200 fail-closed SAN path observation quarantine regressions.

All fixtures are synthetic; no device access or CMDB mutation.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import copy
from itertools import permutations
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from storage_path_risk_v6194 import assess
from storage_dependency_impact_v6199 import map_dependencies


def snapshot(states, independent=False):
    paths = [{'host_id': 'h1', 'storage_id': 'a1',
              'fabric': 'A', 'port': 'p1', 'state': state}
             for state in states]
    if independent:
        paths.append({'host_id': 'h1', 'storage_id': 'a1',
                      'fabric': 'B', 'port': 'p2', 'state': 'up'})
    return {
        'schema': 'storagescope.storage-topology.v1',
        'assets': [{'id': 'h1', 'kind': 'host'},
                   {'id': 'a1', 'kind': 'storage_array',
                    'used_gib': 20, 'total_gib': 100}],
        'paths': paths, 'shares': [],
    }


class StickyPathQuarantineTests(unittest.TestCase):
    def report(self, states, independent=False):
        topology = snapshot(states, independent=independent)
        risk = assess(topology)
        deps = map_dependencies(topology, risk)
        return risk, deps

    def test_up_down_up_is_never_resurrected_in_any_order(self):
        for states in set(permutations(('up', 'down', 'up'))):
            with self.subTest(states=states):
                risk, deps = self.report(states)
                codes = [item['code'] for item in risk['findings']]
                self.assertEqual(risk['verified_active_paths'], 0)
                self.assertEqual(risk['validated_paths'], 1)
                self.assertEqual(risk['assessment'], 'INCOMPLETE')
                self.assertEqual(codes.count('CONFLICTING_PATH_STATE'), 1)
                self.assertIn('NO_VERIFIED_ACTIVE_PATH', codes)
                self.assertEqual(deps['verified_host_relationships'], 0)
                self.assertEqual(deps['unverified_host_relationships'], 1)
                self.assertEqual(deps['assessment'], 'INCOMPLETE')

    def test_invalid_state_poisoned_before_or_after_active_observation(self):
        for states in (('up', 'bogus'), ('bogus', 'up'), ('up', []), ([], 'up')):
            with self.subTest(states=states):
                risk, deps = self.report(states)
                self.assertEqual(risk['verified_active_paths'], 0)
                self.assertEqual(risk['assessment'], 'INCOMPLETE')
                self.assertIn('INVALID_PATH', {f['code'] for f in risk['findings']})
                self.assertEqual(deps['verified_host_relationships'], 0)
                self.assertEqual(deps['unverified_host_relationships'], 1)

    def test_invalid_only_path_never_becomes_verified(self):
        risk, deps = self.report(([],))
        self.assertEqual(risk['verified_active_paths'], 0)
        self.assertEqual(deps['verified_host_relationships'], 0)
        self.assertEqual(deps['unverified_host_relationships'], 1)
        self.assertEqual(deps['assessment'], 'INCOMPLETE')

    def test_independent_fabric_stays_observed_but_incomplete(self):
        risk, deps = self.report(('up', 'down', 'up'), independent=True)
        self.assertEqual(risk['verified_active_paths'], 1)
        self.assertEqual(risk['assessment'], 'INCOMPLETE')
        self.assertIn('SINGLE_ACTIVE_FABRIC', {f['code'] for f in risk['findings']})
        self.assertEqual(deps['verified_host_relationships'], 1)
        self.assertEqual(deps['assessment'], 'INCOMPLETE')

    def test_clean_two_fabric_evidence_is_unchanged(self):
        risk, deps = self.report(('up',), independent=True)
        self.assertEqual(risk['verified_active_paths'], 2)
        self.assertEqual(risk['finding_count'], 0)
        self.assertEqual(deps['verified_host_relationships'], 1)
        self.assertEqual(deps['assessment'], 'OBSERVED_DEPENDENCIES_ONLY')

    def test_repeated_identical_state_not_marked_conflict(self):
        risk, deps = self.report(('up', 'up'), independent=True)
        self.assertEqual(risk['verified_active_paths'], 2)
        self.assertNotIn('CONFLICTING_PATH_STATE',
                         {f['code'] for f in risk['findings']})
        self.assertEqual(deps['verified_host_relationships'], 1)

    def test_input_not_mutated(self):
        topology = snapshot(('up', 'down', 'up'))
        original = copy.deepcopy(topology)
        risk = assess(topology)
        map_dependencies(topology, risk)
        self.assertEqual(topology, original)


if __name__ == '__main__':
    unittest.main()
