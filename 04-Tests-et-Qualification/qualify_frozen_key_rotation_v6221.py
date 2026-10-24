"""V6.221 Windows frozen HMAC key rotation gate; synthetic offline inputs.
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
    old, new = secrets.token_bytes(32), secrets.token_bytes(32)
    env = os.environ.copy()
    env['STORAGESCOPE_HMAC_KEY_OLD_KEY'] = old.hex()
    env['STORAGESCOPE_HMAC_KEY_NEW_KEY'] = new.hex()
    env['STORAGESCOPE_REQUIRE_OBSERVATION_AUTH_V2'] = '1'
    data = {
        'schema': 'storagescope.storage-topology.v1',
        'observation_auth_policy': {
            'schema': 'storagescope.observation-auth-policy.v2',
            'source_keys': {'collector:approved': ['NEW_KEY', 'OLD_KEY']}},
        'assets': [{'id': 'h1', 'kind': 'host'},
                   {'id': 'a1', 'kind': 'storage_array', 'used_gib': 1, 'total_gib': 10},
                   {'id': 'n1', 'kind': 'nas', 'used_gib': 1, 'total_gib': 10}],
        'paths': [sign_observation({'host_id': 'h1', 'storage_id': 'a1',
                                    'fabric': 'A', 'state': 'up',
                                    'source_ref': 'collector:approved'}, 'OLD_KEY', old)],
        'shares': [sign_observation({'id': 's1', 'nas_id': 'n1', 'protocol': 'NFS',
                                     'used_gib': 1, 'quota_gib': 10,
                                     'source_ref': 'collector:approved'}, 'NEW_KEY', new)]}
    with TemporaryDirectory(prefix='storagescope-key-rotation-v6221-') as tmp:
        source, target = Path(tmp) / 'input.json', Path(tmp) / 'report.json'

        def assess(payload):
            target.unlink(missing_ok=True)
            source.write_text(json.dumps(payload, allow_nan=False), encoding='utf-8')
            result = subprocess.run([str(executable), '--storage-risk-file',
                                     str(source), str(target)], env=env,
                                    capture_output=True, text=True, timeout=120)
            return result.returncode, (json.loads(target.read_text(encoding='utf-8'))
                                        if target.exists() else None)

        code, report = assess(data)
        if (code or not report or report['verified_active_paths'] != 1 or
                report['dependency_impact']['verified_share_relationships'] != 1 or
                report['observation_authentication']['verified_observations'] != 2 or
                report['observation_authentication']['rotation_active_sources'] != 1 or
                report['automatic_changes'] != 0):
            raise AssertionError('Frozen two-key rotation verification failed')
        if old.hex() in json.dumps(report) or new.hex() in json.dumps(report):
            raise AssertionError('Secret leaked in frozen rotation report')

        retired = copy.deepcopy(data)
        retired['observation_auth_policy']['source_keys']['collector:approved'] = ['NEW_KEY']
        code, report = assess(retired)
        if (code or not report or report['verified_active_paths'] != 0 or
                report['dependency_impact']['verified_share_relationships'] != 1 or
                report['observation_authentication']['invalid_auth_observations'] != 1):
            raise AssertionError('Retired HMAC key still trusted by frozen executable')

        downgraded = copy.deepcopy(data)
        downgraded['observation_auth_policy'] = {
            'schema': 'storagescope.observation-auth-policy.v1',
            'source_keys': {'collector:approved': 'OLD_KEY'}}
        code, report = assess(downgraded)
        if code == 0 or report is not None:
            raise AssertionError('Frozen executable accepted forbidden v1 downgrade')

        tampered = copy.deepcopy(data)
        tampered['shares'][0]['quota_gib'] = 20
        code, report = assess(tampered)
        if (code or not report or
                report['dependency_impact']['verified_share_relationships'] != 0 or
                report['observation_authentication']['bad_signature_observations'] != 1):
            raise AssertionError('Frozen executable trusted a tampered rotated-key share')
    print('Frozen V6.221 HMAC key rotation, retirement, downgrade and tamper PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=Path, required=True)
    args = parser.parse_args()
    if not args.exe.is_file():
        parser.error('Frozen Windows executable not found')
    run(args.exe.resolve())
