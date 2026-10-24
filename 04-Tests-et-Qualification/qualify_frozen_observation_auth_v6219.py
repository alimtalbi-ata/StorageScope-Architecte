"""Windows-only frozen executable gate for V6.219 (synthetic offline data).
No production key, credential or real infrastructure data. Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from tempfile import TemporaryDirectory

SRC = Path(__file__).resolve().parents[1] / '03-Sources'
sys.path.insert(0, str(SRC))
from storage_observation_auth_v6219 import sign_observation


def run(executable):
    key = secrets.token_bytes(32)
    env = os.environ.copy()
    env['STORAGESCOPE_HMAC_KEY_COLLECTOR_A'] = key.hex()
    original = {
        'schema': 'storagescope.storage-topology.v1',
        'observation_auth_policy': {
            'schema': 'storagescope.observation-auth-policy.v1',
            'source_keys': {'collector:approved': 'COLLECTOR_A'}},
        'assets': [{'id': 'h1', 'kind': 'host'},
                   {'id': 'a1', 'kind': 'storage_array', 'used_gib': 1, 'total_gib': 10},
                   {'id': 'n1', 'kind': 'nas', 'used_gib': 1, 'total_gib': 10}],
        'paths': [sign_observation({'host_id': 'h1', 'storage_id': 'a1',
                                    'fabric': 'A', 'state': 'up',
                                    'source_ref': 'collector:approved'}, 'COLLECTOR_A', key)],
        'shares': [sign_observation({'id': 's1', 'nas_id': 'n1', 'protocol': 'NFS',
                                     'used_gib': 1, 'quota_gib': 10,
                                     'source_ref': 'collector:approved'}, 'COLLECTOR_A', key)],
    }
    with TemporaryDirectory(prefix='storagescope-auth-v6219-') as tmp:
        root = Path(tmp)
        def check(case, topology, environment, expected_verified, expected_paths, expected_shares):
            source = root / (case + '.json')
            target = root / (case + '-report.json')
            source.write_text(json.dumps(topology, ensure_ascii=False, allow_nan=False), encoding='utf-8')
            completed = subprocess.run([str(executable), '--storage-risk-file', str(source), str(target)],
                                       env=environment, capture_output=True, text=True, timeout=120)
            if completed.returncode != 0 or not target.is_file():
                raise AssertionError(f'Frozen {case} execution failed: exit={completed.returncode}')
            report = json.loads(target.read_text(encoding='utf-8'))
            deps = report['dependency_impact']
            auth = report['observation_authentication']
            if (auth['verified_observations'] != expected_verified or
                    report['verified_active_paths'] != expected_paths or
                    deps['verified_share_relationships'] != expected_shares or
                    deps['observation_authentication']['verified_observations'] != expected_verified or
                    report['automatic_changes'] != 0 or deps['automatic_changes'] != 0):
                raise AssertionError(f'Frozen {case} authentication or quarantine mismatch')
            if case != 'valid' and report['assessment'] != 'INCOMPLETE':
                raise AssertionError(f'Frozen {case} incorrectly marked complete')
            if key.hex() in json.dumps(report):
                raise AssertionError('HMAC key leaked in frozen report')

        check('valid', original, env, 2, 1, 1)
        tampered = json.loads(json.dumps(original))
        tampered['paths'][0]['state'] = 'down'
        tampered['shares'][0]['quota_gib'] = 100
        check('tampered', tampered, env, 0, 0, 0)
        without_key = dict(env)
        without_key.pop('STORAGESCOPE_HMAC_KEY_COLLECTOR_A', None)
        check('missing-key', original, without_key, 0, 0, 0)
    print('Frozen V6.219 HMAC authentication PASS (synthetic, no real secrets, read-only)')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', required=True, type=Path)
    args = parser.parse_args()
    if not args.exe.is_file():
        parser.error('Frozen Windows executable not found')
    run(args.exe.resolve())


if __name__ == '__main__':
    main()
