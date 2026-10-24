"""V6.222 frozen Windows executable: persistent anti-replay, synthetic only.
Author: Abdelhalim Talbi.
"""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from storage_observation_auth_v6219 import sign_observation


def run(executable):
    secret = secrets.token_bytes(32)
    env = os.environ.copy()
    env['STORAGESCOPE_HMAC_KEY_KEY_A'] = secret.hex()
    env['STORAGESCOPE_REQUIRE_OBSERVATION_AUTH_V2'] = '1'

    def snapshot(collection_id):
        record = {'host_id': 'h1', 'storage_id': 'a1', 'fabric': 'A', 'state': 'up',
                  'source_ref': 'collector:a', 'collection_id': collection_id,
                  'observed_at': '2026-10-24T10:00:00Z'}
        return {'schema': 'storagescope.storage-topology.v1',
                'observation_auth_policy': {
                    'schema': 'storagescope.observation-auth-policy.v2',
                    'source_keys': {'collector:a': ['KEY_A']}},
                'assets': [{'id': 'h1', 'kind': 'host'},
                           {'id': 'a1', 'kind': 'storage_array', 'used_gib': 10,
                            'total_gib': 100}],
                'paths': [sign_observation(record, 'KEY_A', secret)], 'shares': []}

    with TemporaryDirectory(prefix='storagescope-v6222-replay-') as tmp:
        root = Path(tmp)
        ledger = root / 'ledger.sqlite'
        source = root / 'snapshot.json'

        def invoke(*args):
            return subprocess.run([str(executable), *map(str, args)], env=env,
                                  capture_output=True, text=True, timeout=120)

        init = invoke('--storage-replay-init', ledger)
        if init.returncode or json.loads(init.stdout)['status'] != 'INITIALIZED':
            raise AssertionError('Frozen ledger initialization failed')
        first = snapshot(str(uuid4()))
        source.write_text(json.dumps(first), encoding='utf-8')
        accepted = invoke('--storage-replay-register', source, ledger)
        if accepted.returncode or json.loads(accepted.stdout)['status'] != 'ACCEPTED':
            raise AssertionError('Frozen signed collection not accepted')
        replay = invoke('--storage-replay-register', source, ledger)
        if replay.returncode == 0 or 'REPLAY_DETECTED' not in replay.stderr:
            raise AssertionError('Frozen cross-snapshot replay accepted')
        if secret.hex() in (accepted.stdout + replay.stderr):
            raise AssertionError('HMAC secret leaked in frozen output')
        tampered = snapshot(str(uuid4()))
        tampered['paths'][0]['state'] = 'down'
        source.write_text(json.dumps(tampered), encoding='utf-8')
        if invoke('--storage-replay-register', source, ledger).returncode == 0:
            raise AssertionError('Frozen executable accepted tampered signature')
        second = snapshot(str(uuid4()))
        source.write_text(json.dumps(second), encoding='utf-8')
        if invoke('--storage-replay-register', source, ledger).returncode:
            raise AssertionError('Frozen executable rejected independent collection')
        with closing(sqlite3.connect(ledger)) as db:
            if db.execute('SELECT COUNT(*) FROM collection_seen').fetchone()[0] != 2:
                raise AssertionError('Frozen ledger transaction count incorrect')
        ledger.unlink()
        if invoke('--storage-replay-register', source, ledger).returncode == 0 or ledger.exists():
            raise AssertionError('Frozen executable silently recreated missing ledger')
    print('Frozen V6.222 SQLite replay ledger, tamper, concurrency-safe key and fail-closed PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=Path, required=True)
    args = parser.parse_args()
    if not args.exe.is_file():
        parser.error('Frozen executable missing')
    run(args.exe.resolve())
