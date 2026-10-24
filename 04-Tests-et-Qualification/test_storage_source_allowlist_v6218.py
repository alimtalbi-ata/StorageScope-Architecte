"""V6.218 operator-declared source screening; synthetic, no live collectors.
Author: Abdelhalim Talbi.
"""
import copy
import pathlib
import sys
import unittest

SRC = pathlib.Path(__file__).resolve().parents[1] / '03-Sources'
sys.path.insert(0, str(SRC))
from storage_path_risk_v6194 import assess
from storage_dependency_impact_v6199 import map_dependencies
from storage_risk_desktop_v6196 import format_risk_report


def topology():
    return {
        'schema': 'storagescope.storage-topology.v1',
        'source_policy': {'schema': 'storagescope.observation-source-policy.v1',
                          'allowed_source_refs': ['collector:approved']},
        'assets': [{'id': 'host1', 'kind': 'host'},
                   {'id': 'array1', 'kind': 'storage_array', 'used_gib': 5, 'total_gib': 10},
                   {'id': 'nas1', 'kind': 'nas', 'used_gib': 5, 'total_gib': 10}],
        'paths': [{'host_id': 'host1', 'storage_id': 'array1', 'fabric': 'A',
                   'state': 'up', 'source_ref': 'collector:approved'}],
        'shares': [{'id': 'share1', 'nas_id': 'nas1', 'protocol': 'NFS',
                    'source_ref': 'collector:approved', 'used_gib': 5, 'quota_gib': 10}],
    }


def evaluate(data):
    risk = assess(data)
    return risk, map_dependencies(data, risk)


class SourceAllowlistTests(unittest.TestCase):
    def test_approved_source_is_observed_but_not_authenticated(self):
        risk, deps = evaluate(topology())
        self.assertEqual(risk['verified_active_paths'], 1)
        self.assertEqual(deps['verified_share_relationships'], 1)
        self.assertEqual(deps['source_evaluation']['allowed_observations'], 2)
        self.assertEqual(deps['source_evaluation']['authentication'], 'NOT_AUTHENTICATED')

    def test_unlisted_path_cannot_verify_connectivity(self):
        data = topology()
        data['paths'][0]['source_ref'] = 'collector:unlisted'
        risk, deps = evaluate(data)
        self.assertEqual(risk['assessment'], 'INCOMPLETE')
        self.assertEqual(risk['verified_active_paths'], 0)
        self.assertEqual(deps['verified_host_relationships'], 0)
        self.assertEqual(deps['unverified_host_relationships'], 1)
        self.assertEqual(deps['source_evaluation']['unlisted_observations'], 1)
        self.assertTrue(any(f['code'] == 'UNTRUSTED_PATH_SOURCE' for f in risk['findings']))

    def test_bad_duplicate_path_poison_is_order_independent(self):
        data = topology()
        bad = copy.deepcopy(data['paths'][0])
        bad['source_ref'] = 'collector:unlisted'
        for records in ([data['paths'][0], bad], [bad, data['paths'][0]]):
            sample = copy.deepcopy(data)
            sample['paths'] = copy.deepcopy(records)
            risk, deps = evaluate(sample)
            self.assertEqual(risk['verified_active_paths'], 0)
            self.assertEqual(deps['verified_host_relationships'], 0)
            self.assertEqual(deps['unverified_host_relationships'], 1)

    def test_missing_source_path_and_share_are_quarantined(self):
        data = topology()
        data['paths'][0].pop('source_ref')
        data['shares'][0].pop('source_ref')
        risk, deps = evaluate(data)
        self.assertEqual(deps['source_evaluation']['missing_observations'], 2)
        self.assertEqual(deps['verified_share_relationships'], 0)
        self.assertEqual(deps['unresolved_share_observations'], 1)
        self.assertIn('UNTRUSTED_SHARE_SOURCE', {f['code'] for f in risk['findings']})

    def test_invalid_source_id_does_not_leak_into_report(self):
        data = topology()
        data['paths'][0]['source_ref'] = 'token=PRIVATE_TEST_VALUE'
        risk, deps = evaluate(data)
        self.assertEqual(deps['source_evaluation']['invalid_observations'], 1)
        self.assertNotIn('PRIVATE_TEST_VALUE', repr(risk) + repr(deps))

    def test_reject_duplicate_or_malformed_allowlists(self):
        for refs in ([], ['approved', 'approved'], ['ok', 'bad key'], [1],
                     ['x' * 129], ['ok'] * 129):
            data = topology()
            data['source_policy']['allowed_source_refs'] = refs
            with self.subTest(refs=repr(refs)[:40]), self.assertRaises(ValueError):
                evaluate(data)

    def test_reject_unknown_policy_fields(self):
        data = topology()
        data['source_policy']['signature_verified'] = True
        with self.assertRaises(ValueError):
            evaluate(data)

    def test_legacy_snapshots_without_policy_remain_compatible(self):
        data = topology()
        data.pop('source_policy')
        data['paths'][0].pop('source_ref')
        data['shares'][0].pop('source_ref')
        risk, deps = evaluate(data)
        self.assertEqual(risk['verified_active_paths'], 1)
        self.assertEqual(deps['verified_share_relationships'], 1)
        self.assertIsNone(deps['source_evaluation'])

    def test_read_only_deterministic_and_windows_text_disclaimer(self):
        data = topology()
        original = copy.deepcopy(data)
        risk, deps = evaluate(data)
        risk['dependency_impact'] = deps
        self.assertEqual(data, original)
        self.assertEqual((assess(data), map_dependencies(data, assess(data))), evaluate(data))
        self.assertEqual(risk['automatic_changes'], 0)
        self.assertEqual(deps['automatic_changes'], 0)
        text = format_risk_report(risk)
        self.assertIn('NON AUTHENTIFIÉE', text)
        self.assertIn('Observations de sources autorisées : 2', text)


if __name__ == '__main__':
    unittest.main()
