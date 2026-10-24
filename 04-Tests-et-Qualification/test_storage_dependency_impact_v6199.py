"""V6.199 dependency blast-radius evidence and export integrity regression tests.
Author: Abdelhalim Talbi.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / '03-Sources'
sys.path.insert(0, str(SOURCE))
from storage_risk_desktop_v6196 import assess_topology_file, export_risk_report, format_risk_report


def topology():
    return {'schema': 'storagescope.storage-topology.v1',
            'assets': [{'id': 'h1', 'kind': 'host'},
                       {'id': 'a1', 'kind': 'storage_array', 'used_gib': 20, 'total_gib': 100},
                       {'id': 'n1', 'kind': 'nas', 'used_gib': 20, 'total_gib': 100}],
            'paths': [{'host_id': 'h1', 'storage_id': 'a1', 'fabric': 'A', 'state': 'up'},
                      {'host_id': 'h1', 'storage_id': 'a1', 'fabric': 'B', 'state': 'up'}],
            'shares': [{'id': 's1', 'nas_id': 'n1', 'protocol': 'NFS', 'used_gib': 10, 'quota_gib': 100}]}


class DependencyImpactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'topology.json'

    def assess(self, data):
        self.source.write_text(json.dumps(data), encoding='utf-8')
        return assess_topology_file(self.source)['dependency_impact']

    def test_verified_paths_and_nas_shares(self):
        result = self.assess(topology())
        self.assertEqual(result['assessment'], 'OBSERVED_DEPENDENCIES_ONLY')
        self.assertEqual(result['verified_host_relationships'], 1)
        self.assertEqual(result['verified_share_relationships'], 1)
        self.assertEqual(result['assets'][0]['verified_host_ids'], ['h1'])
        self.assertEqual(result['assets'][1]['verified_share_ids'], ['s1'])
        self.assertEqual(result['automatic_changes'], 0)

    def test_unknown_path_never_verified(self):
        data = topology()
        data['paths'] = [dict(data['paths'][0], state='unknown')]
        result = self.assess(data)
        self.assertEqual(result['verified_host_relationships'], 0)
        self.assertEqual(result['unverified_host_relationships'], 1)
        self.assertEqual(result['assessment'], 'INCOMPLETE')
        self.assertEqual(result['assets'][0]['unverified_host_ids'], ['h1'])

    def test_conflicting_duplicate_state_is_fail_closed(self):
        data = topology()
        data['paths'] = [dict(data['paths'][0], state='up'), dict(data['paths'][0], state='down')]
        result = self.assess(data)
        self.assertEqual(result['verified_host_relationships'], 0)
        self.assertEqual(result['unverified_host_relationships'], 1)

    def test_conflict_on_one_fabric_does_not_hide_other_verified_fabric(self):
        data = topology()
        data['paths'].append(dict(data['paths'][0], state='down'))
        result = self.assess(data)
        self.assertEqual(result['verified_host_relationships'], 1)
        self.assertEqual(result['unverified_host_relationships'], 1)
        self.assertEqual(result['mixed_evidence_host_relationships'], 1)
        self.assertEqual(result['assessment'], 'INCOMPLETE')
        self.assertEqual(result['assets'][0]['verified_host_ids'], ['h1'])
        self.assertEqual(result['assets'][0]['mixed_evidence_host_ids'], ['h1'])

    def test_duplicate_asset_id_never_creates_trusted_dependency(self):
        data = topology()
        data['assets'].append({'id': 'a1', 'kind': 'nas'})
        result = self.assess(data)
        self.assertEqual(result['verified_host_relationships'], 0)
        self.assertEqual(result['assessment'], 'INCOMPLETE')
        self.assertEqual([a['asset_id'] for a in result['assets']], ['n1'])

    def test_duplicate_share_id_not_counted(self):
        data = topology()
        data['shares'].append(dict(data['shares'][0]))
        result = self.assess(data)
        self.assertEqual(result['verified_share_relationships'], 0)
        self.assertEqual(result['assessment'], 'INCOMPLETE')

    def test_unresolved_orphan_paths_not_counted(self):
        data = topology()
        data['paths'].append({'host_id': 'unknown', 'storage_id': 'a1', 'fabric': 'X', 'state': 'up'})
        result = self.assess(data)
        self.assertEqual(result['verified_host_relationships'], 1)
        self.assertEqual(result['assessment'], 'INCOMPLETE')

    def test_unassessed_asset_never_claims_zero_impact(self):
        data = topology()
        data['paths'] = []
        result = self.assess(data)
        self.assertEqual(result['assessment'], 'INCOMPLETE')
        self.assertEqual(result['assets'][0]['scope'], 'UNASSESSED')

    def test_deterministic_and_no_input_mutation(self):
        from storage_path_risk_v6194 import assess
        from storage_dependency_impact_v6199 import map_dependencies
        data = topology()
        original = copy.deepcopy(data)
        result = map_dependencies(data, assess(data))
        self.assertEqual(result, map_dependencies(data, assess(data)))
        self.assertEqual(data, original)

    def test_gui_projection_shows_verified_and_unknown_dependencies(self):
        data = topology()
        data['paths'] = [dict(data['paths'][0], state='down')]
        self.source.write_text(json.dumps(data), encoding='utf-8')
        rendered = format_risk_report(assess_topology_file(self.source), limit=1)
        self.assertIn('Relations hôtes non vérifiées : 1', rendered)
        self.assertIn('équipements supplémentaires non affichés', rendered)
        self.assertIn('sans impact applicatif présumé', rendered)

    def test_export_contains_dependency_evidence_and_refuses_overwrite(self):
        self.source.write_text(json.dumps(topology()), encoding='utf-8')
        output = self.source.parent / 'evidence.json'
        export_risk_report(self.source, output)
        content = output.read_bytes()
        self.assertEqual(json.loads(content)['dependency_impact']['verified_host_relationships'], 1)
        with self.assertRaises(FileExistsError):
            export_risk_report(self.source, output)
        self.assertEqual(content, output.read_bytes())

    def test_partial_write_failure_removes_only_our_new_file(self):
        self.source.write_text(json.dumps(topology()), encoding='utf-8')
        output = self.source.parent / 'partial.json'
        real_open = Path.open

        class FailingStream:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args): return self.stream.__exit__(*args)
            def write(self, content):
                self.stream.write(content[:10])
                raise OSError('simulated disk full')
            def flush(self): return self.stream.flush()

        def fake_open(path, *args, **kwargs):
            stream = real_open(path, *args, **kwargs)
            return FailingStream(stream) if Path(path) == output else stream

        with patch.object(Path, 'open', fake_open):
            with self.assertRaisesRegex(OSError, 'simulated disk full'):
                export_risk_report(self.source, output)
        self.assertFalse(output.exists())

    def test_close_failure_removes_partial_output(self):
        self.source.write_text(json.dumps(topology()), encoding='utf-8')
        output = self.source.parent / 'partial-close.json'
        real_open = Path.open

        class FailingClose:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args):
                self.stream.close()
                raise OSError('simulated close failure')
            def write(self, value): return self.stream.write(value)
            def flush(self): return self.stream.flush()

        def fake_open(path, *args, **kwargs):
            stream = real_open(path, *args, **kwargs)
            return FailingClose(stream) if Path(path) == output else stream

        with patch.object(Path, 'open', fake_open):
            with self.assertRaisesRegex(OSError, 'simulated close failure'):
                export_risk_report(self.source, output)
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
