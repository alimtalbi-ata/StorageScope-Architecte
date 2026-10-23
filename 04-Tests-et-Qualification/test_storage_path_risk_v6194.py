"""StorageScope v6.194 — topology risk regression tests, no external dependencies."""
import copy
import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import json
import unittest

SOURCE = pathlib.Path(__file__).resolve().parents[1] / '03-Sources' / 'storage_path_risk_v6194.py'
spec = importlib.util.spec_from_file_location('storage_path_risk_v6194', SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def topo(assets=None, paths=None, shares=None):
    return {'schema': 'storagescope.storage-topology.v1', 'assets': assets or [],
            'paths': paths or [], 'shares': shares or []}


HOST = {'id': 'h1', 'kind': 'host'}
ARRAY = {'id': 'a1', 'kind': 'storage_array', 'used_gib': 20, 'total_gib': 100}
NAS = {'id': 'n1', 'kind': 'nas', 'used_gib': 20, 'total_gib': 100}


def path(fabric, state='up', port=None):
    return {'host_id': 'h1', 'storage_id': 'a1', 'fabric': fabric, 'state': state, 'port': port}


class RiskTests(unittest.TestCase):
    def codes(self, report):
        return {f['code'] for f in report['findings']}

    def test_empty_assessment_is_not_claimed_safe(self):
        self.assertEqual(mod.assess(topo())['assessment'], 'NO_FINDINGS_IN_ASSESSED_SCOPE')

    def test_two_independent_fabrics(self):
        report = mod.assess(topo([HOST, ARRAY], [path('A'), path('B')]))
        self.assertEqual(report['finding_count'], 0)
        self.assertEqual(report['validated_paths'], 2)

    def test_same_fabric_two_ports_not_redundant(self):
        report = mod.assess(topo([HOST, ARRAY], [path('A', port='p1'), path('A', port='p2')]))
        self.assertIn('SINGLE_ACTIVE_FABRIC', self.codes(report))

    def test_duplicate_path_does_not_count_twice(self):
        report = mod.assess(topo([HOST, ARRAY], [path('A'), path('A')]))
        self.assertIn('DUPLICATE_PATH_EVIDENCE', self.codes(report))
        self.assertEqual(report['validated_paths'], 1)

    def test_down_paths_and_no_active(self):
        report = mod.assess(topo([HOST, ARRAY], [path('A', 'down')]))
        self.assertIn('NO_VERIFIED_ACTIVE_PATH', self.codes(report))
        self.assertIn('PATH_DOWN', self.codes(report))

    def test_unknown_not_healthy(self):
        report = mod.assess(topo([HOST, ARRAY], [path('A', 'unknown')]))
        self.assertIn('NO_VERIFIED_ACTIVE_PATH', self.codes(report))
        self.assertIn('PATH_STATE_UNKNOWN', self.codes(report))

    def test_no_path_evidence_is_unassessed(self):
        report = mod.assess(topo([HOST, ARRAY]))
        self.assertEqual(report['assessment'], 'INCOMPLETE')
        self.assertIn('HOST_PATHS_UNASSESSED', self.codes(report))
        self.assertIn('ARRAY_PATHS_UNASSESSED', self.codes(report))

    def test_orphan_endpoint_is_invalid(self):
        report = mod.assess(topo([HOST], [path('A')]))
        self.assertIn('ORPHAN_PATH', self.codes(report))
        self.assertEqual(report['invalid_records'], 1)

    def test_duplicate_asset_is_not_silently_merged(self):
        report = mod.assess(topo([HOST, HOST]))
        self.assertIn('DUPLICATE_ASSET', self.codes(report))
        self.assertEqual(report['assets'], 1)

    def test_capacity_thresholds(self):
        report = mod.assess(topo([{'id':'n1','kind':'nas','used_gib':96,'total_gib':100},
                                  {'id':'n2','kind':'nas','used_gib':86,'total_gib':100}]))
        self.assertIn('CAPACITY_CRITICAL', self.codes(report))
        self.assertIn('CAPACITY_WARNING', self.codes(report))

    def test_invalid_capacity_bool_nan_and_overcommit(self):
        for used, total in [(True, 100), (float('nan'), 100), (101, 100), (0, 0)]:
            with self.subTest(used=used, total=total):
                report = mod.assess(topo([{'id':'n1','kind':'nas','used_gib':used,'total_gib':total}]))
                self.assertIn('INVALID_CAPACITY', self.codes(report))

    def test_nas_share_quota(self):
        report = mod.assess(topo([NAS], shares=[{'id':'s1','nas_id':'n1','protocol':'NFS',
                                                 'used_gib':97,'quota_gib':100}]))
        self.assertIn('SHARE_QUOTA_CRITICAL', self.codes(report))

    def test_unknown_share_protocol(self):
        report = mod.assess(topo([NAS], shares=[{'id':'s1','nas_id':'n1','protocol':'FTP'}]))
        self.assertIn('INVALID_SHARE', self.codes(report))

    def test_no_mutation_and_determinism(self):
        original = topo([HOST, ARRAY], [path('B'), path('A')])
        before = copy.deepcopy(original)
        self.assertEqual(mod.assess(original), mod.assess(original))
        self.assertEqual(original, before)

    def test_untrusted_nested_types_are_findings_not_crashes(self):
        report = mod.assess(topo([{'id':'bad','kind':[]} , HOST, ARRAY, NAS],
                                 [dict(path('A'), state=[])],
                                 [{'id':'s','nas_id':'n1','protocol':[]}]))
        self.assertIn('INVALID_ASSET', self.codes(report))
        self.assertIn('INVALID_PATH', self.codes(report))
        self.assertIn('INVALID_SHARE', self.codes(report))

    def test_bad_schema_and_thresholds(self):
        with self.assertRaises(ValueError): mod.assess({})
        with self.assertRaises(ValueError): mod.assess(topo(), 95, 85)

    def test_cli_json_and_exit_code(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / 'input.json'
            out = pathlib.Path(d) / 'report.json'
            p.write_text(json.dumps(topo([HOST, ARRAY], [path('A'), path('B')])), encoding='utf-8')
            completed = subprocess.run([sys.executable, str(SOURCE), str(p), '--output', str(out)],
                                       capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(out.read_text(encoding='utf-8'))['finding_count'], 0)


if __name__ == '__main__':
    unittest.main()
