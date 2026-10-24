"""V6.217: unrounded capacity/quota thresholds, synthetic offline tests.
Author: Abdelhalim Talbi.
"""
import copy
import importlib.util
import pathlib
import sys
import unittest

SOURCE = pathlib.Path(__file__).resolve().parents[1] / '03-Sources' / 'storage_path_risk_v6194.py'
sys.path.insert(0, str(SOURCE.parent))
spec = importlib.util.spec_from_file_location('storage_path_risk_v6194', SOURCE)
risk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(risk)


def topology(assets, shares=()):
    return {'schema': 'storagescope.storage-topology.v1', 'assets': assets,
            'paths': [], 'shares': list(shares)}


def codes(report, ident):
    return {item['code'] for item in report['findings'] if item['object_id'] == ident}


class ThresholdPrecisionTests(unittest.TestCase):
    def assess_capacity(self, used):
        return risk.assess(topology([{'id': 'nas1', 'kind': 'nas',
                                     'used_gib': used, 'total_gib': 100}]))

    def assess_share(self, used):
        return risk.assess(topology([{'id': 'nas1', 'kind': 'nas',
                                     'used_gib': 10, 'total_gib': 100}],
                                    [{'id': 'share1', 'nas_id': 'nas1', 'protocol': 'NFS',
                                      'used_gib': used, 'quota_gib': 100}]))

    def test_capacity_below_warning_must_not_round_into_warning(self):
        report = self.assess_capacity(84.9999)
        self.assertNotIn('CAPACITY_WARNING', codes(report, 'nas1'))
        self.assertNotIn('CAPACITY_CRITICAL', codes(report, 'nas1'))

    def test_capacity_below_critical_is_warning_not_critical(self):
        report = self.assess_capacity(94.9999)
        self.assertIn('CAPACITY_WARNING', codes(report, 'nas1'))
        self.assertNotIn('CAPACITY_CRITICAL', codes(report, 'nas1'))
        finding = next(f for f in report['findings'] if f['code'] == 'CAPACITY_WARNING')
        self.assertNotIn('95% used', finding['evidence'])

    def test_capacity_exact_boundaries_remain_inclusive(self):
        self.assertIn('CAPACITY_WARNING', codes(self.assess_capacity(85), 'nas1'))
        self.assertIn('CAPACITY_CRITICAL', codes(self.assess_capacity(95), 'nas1'))

    def test_share_below_warning_must_not_round_into_warning(self):
        report = self.assess_share(84.9999)
        self.assertNotIn('SHARE_QUOTA_WARNING', codes(report, 'share1'))
        self.assertNotIn('SHARE_QUOTA_CRITICAL', codes(report, 'share1'))

    def test_share_below_critical_is_warning_not_critical(self):
        report = self.assess_share(94.9999)
        self.assertIn('SHARE_QUOTA_WARNING', codes(report, 'share1'))
        self.assertNotIn('SHARE_QUOTA_CRITICAL', codes(report, 'share1'))

    def test_share_exact_boundaries_remain_inclusive(self):
        self.assertIn('SHARE_QUOTA_WARNING', codes(self.assess_share(85), 'share1'))
        self.assertIn('SHARE_QUOTA_CRITICAL', codes(self.assess_share(95), 'share1'))

    def test_read_only_and_repeatable_at_boundary(self):
        data = topology([{'id': 'nas1', 'kind': 'nas', 'used_gib': 94.9999,
                          'total_gib': 100}],
                        [{'id': 'share1', 'nas_id': 'nas1', 'protocol': 'SMB',
                          'used_gib': 84.9999, 'quota_gib': 100}])
        original = copy.deepcopy(data)
        self.assertEqual(risk.assess(data), risk.assess(data))
        self.assertEqual(data, original)
        self.assertEqual(risk.assess(data)['automatic_changes'], 0)


if __name__ == '__main__':
    unittest.main()
