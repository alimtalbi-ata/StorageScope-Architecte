"""V6.220 frozen Windows replay gate, synthetic offline data only.
Author: Abdelhalim Talbi.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from storage_observation_auth_v6219 import sign_observation


def run(executable):
    key = secrets.token_bytes(32)
    env = os.environ.copy()
    env['STORAGESCOPE_HMAC_KEY_COLLECTOR_A'] = key.hex()
    path = sign_observation({'host_id': 'h1', 'storage_id': 'a1',
                             'fabric': 'A', 'state': 'up',
                             'source_ref': 'collector:approved'}, 'COLLECTOR_A', key)
    share = sign_observation({'id': 's1', 'nas_id': 'n1', 'protocol': 'NFS',
                              'used_gib': 1, 'quota_gib': 10,
                              'source_ref': 'collector:approved'}, 'COLLECTOR_A', key)
    data = {'schema': 'storagescope.storage-topology.v1',
            'observation_auth_policy': {
                'schema': 'storagescope.observation-auth-policy.v1',
                'source_keys': {'collector:approved': 'COLLECTOR_A'}},
            'assets': [{'id': 'h1', 'kind': 'host'},
                       {'id': 'a1', 'kind': 'storage_array', 'used_gib': 1, 'total_gib': 10},
                       {'id': 'n1', 'kind': 'nas', 'used_gib': 1, 'total_gib': 10}],
            'paths': [path, copy.deepcopy(path)],
            'shares': [share, copy.deepcopy(share)]}
    with TemporaryDirectory(prefix='storagescope-replay-v6220-') as tmp:
        source, target = Path(tmp) / 'input.json', Path(tmp) / 'report.json'
        source.write_text(json.dumps(data, allow_nan=False), encoding='utf-8')
        result = subprocess.run([str(executable), '--storage-risk-file',
                                 str(source), str(target)], env=env,
                                capture_output=True, text=True, timeout=120)
        if result.returncode != 0 or not target.is_file():
            raise AssertionError(f'Frozen replay assessment failed: exit={result.returncode}')
        report = json.loads(target.read_text(encoding='utf-8'))
        deps = report['dependency_impact']
        codes = [f['code'] for f in report['findings']]
        if (report['assessment'] != 'INCOMPLETE' or
                report['verified_active_paths'] != 0 or
                report['replayed_path_observations'] != 2 or
                report['replayed_share_observations'] != 2 or
                deps['verified_host_relationships'] != 0 or
                deps['verified_share_relationships'] != 0 or
                deps['replayed_path_observations'] != 2 or
                deps['replayed_share_observations'] != 2 or
                codes.count('REPLAYED_PATH_OBSERVATION') != 2 or
                codes.count('REPLAYED_SHARE_OBSERVATION') != 2 or
                report['automatic_changes'] != 0 or
                deps['automatic_changes'] != 0):
            raise AssertionError('Frozen replay quarantine or dependency evidence mismatch')
        if key.hex() in json.dumps(report):
            raise AssertionError('Secret leaked in replay report')
    print('Frozen V6.220 signed intra-snapshot replay quarantine PASS (synthetic)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=Path, required=True)
    args = parser.parse_args()
    if not args.exe.is_file():
        parser.error('Frozen Windows executable not found')
    run(args.exe.resolve())
