"""V6.222 transactional cross-snapshot replay ledger, synthetic only.
Author: Abdelhalim Talbi.
"""
import copy
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from storage_observation_auth_v6219 import sign_observation
from storage_replay_ledger_v6222 import initialize_ledger, register_snapshot
from storage_path_risk_v6194 import assess

SECRET = bytes(range(32))
SECRET2 = bytes(range(32, 64))


def snapshot(collection_id=None, source='collector:a', key_id='KEY_A', secret=SECRET):
    collection_id = collection_id or str(uuid4())
    record = {'host_id': 'h1', 'storage_id': 'a1', 'fabric': 'A', 'state': 'up',
              'source_ref': source, 'collection_id': collection_id,
              'observed_at': '2026-10-24T10:00:00Z'}
    return {'schema': 'storagescope.storage-topology.v1',
            'observation_auth_policy': {'schema': 'storagescope.observation-auth-policy.v2',
                                        'source_keys': {source: [key_id]}},
            'assets': [{'id': 'h1', 'kind': 'host'},
                       {'id': 'a1', 'kind': 'storage_array', 'used_gib': 10,
                        'total_gib': 100}],
            'paths': [sign_observation(record, key_id, secret)], 'shares': []}


class ReplayLedgerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.ledger = self.root / 'replay.sqlite'
        env = patch.dict(os.environ, {'STORAGESCOPE_HMAC_KEY_KEY_A': SECRET.hex(),
                                      'STORAGESCOPE_HMAC_KEY_KEY_B': SECRET2.hex()})
        env.start()
        self.addCleanup(env.stop)

    def rows(self):
        with closing(sqlite3.connect(self.ledger)) as db:
            return db.execute('SELECT source_ref, collection_id FROM collection_seen ORDER BY 1, 2').fetchall()

    def test_explicit_init_and_single_acceptance(self):
        self.assertEqual(initialize_ledger(self.ledger)['status'], 'INITIALIZED')
        data = snapshot()
        before = copy.deepcopy(data)
        receipt = register_snapshot(data, self.ledger)
        self.assertEqual(data, before)
        self.assertEqual(receipt['registered_observations'], 1)
        self.assertEqual(receipt['automatic_changes'], 0)
        self.assertEqual(len(self.rows()), 1)
        self.assertNotIn(SECRET.hex(), repr(receipt))

    def test_replay_between_snapshots_rejected_without_new_rows(self):
        initialize_ledger(self.ledger)
        data = snapshot()
        register_snapshot(data, self.ledger)
        with self.assertRaisesRegex(ValueError, 'REPLAY_DETECTED'):
            register_snapshot(copy.deepcopy(data), self.ledger)
        self.assertEqual(len(self.rows()), 1)

    def test_reuse_collection_id_with_new_signed_payload_rejected(self):
        initialize_ledger(self.ledger)
        data = snapshot()
        register_snapshot(data, self.ledger)
        changed = copy.deepcopy(data)
        changed['paths'][0]['fabric'] = 'B'
        changed['paths'][0] = sign_observation(changed['paths'][0], 'KEY_A', SECRET)
        with self.assertRaisesRegex(ValueError, 'REPLAY_DETECTED'):
            register_snapshot(changed, self.ledger)

    def test_distinct_collection_accepted_and_no_silent_reinit(self):
        initialize_ledger(self.ledger)
        register_snapshot(snapshot(), self.ledger)
        register_snapshot(snapshot(), self.ledger)
        self.assertEqual(len(self.rows()), 2)
        with self.assertRaises(FileExistsError):
            initialize_ledger(self.ledger)
        self.ledger.unlink()
        with self.assertRaisesRegex(ValueError, 'explicit initialization'):
            register_snapshot(snapshot(), self.ledger)
        self.assertFalse(self.ledger.exists())

    def test_tampered_and_unsigned_observations_never_consume_ids(self):
        initialize_ledger(self.ledger)
        for mutation in ('tamper', 'missing_auth', 'missing_time', 'bad_id'):
            with self.subTest(mutation=mutation):
                data = snapshot()
                if mutation == 'tamper':
                    data['paths'][0]['state'] = 'down'
                elif mutation == 'missing_auth':
                    del data['paths'][0]['auth']
                elif mutation == 'missing_time':
                    del data['paths'][0]['observed_at']
                    data['paths'][0] = sign_observation(data['paths'][0], 'KEY_A', SECRET)
                else:
                    data['paths'][0]['collection_id'] = 'not-a-uuid'
                    data['paths'][0] = sign_observation(data['paths'][0], 'KEY_A', SECRET)
                with self.assertRaises(ValueError):
                    register_snapshot(data, self.ledger)
        self.assertEqual(self.rows(), [])

    def test_policy_downgrade_and_legacy_not_accepted(self):
        initialize_ledger(self.ledger)
        data = snapshot()
        data['observation_auth_policy'] = {'schema': 'storagescope.observation-auth-policy.v1',
                                           'source_keys': {'collector:a': 'KEY_A'}}
        with self.assertRaisesRegex(ValueError, 'policy v2'):
            register_snapshot(data, self.ledger)
        del data['observation_auth_policy']
        with self.assertRaisesRegex(ValueError, 'policy v2'):
            register_snapshot(data, self.ledger)
        self.assertEqual(self.rows(), [])

    def test_intra_snapshot_duplicate_rejected_without_writes(self):
        initialize_ledger(self.ledger)
        data = snapshot()
        data['paths'].append(copy.deepcopy(data['paths'][0]))
        with self.assertRaisesRegex(ValueError, 'Repeated signed'):
            register_snapshot(data, self.ledger)
        self.assertEqual(self.rows(), [])

    def test_multi_source_batch_rollback_if_one_replayed(self):
        initialize_ledger(self.ledger)
        old = snapshot(source='collector:b', key_id='KEY_B', secret=SECRET2)
        register_snapshot(old, self.ledger)
        mixed = snapshot(source='collector:a')
        mixed['observation_auth_policy']['source_keys']['collector:b'] = ['KEY_B']
        mixed['paths'].extend(copy.deepcopy(old['paths']))
        with self.assertRaisesRegex(ValueError, 'REPLAY_DETECTED'):
            register_snapshot(mixed, self.ledger)
        self.assertEqual(self.rows(), [('collector:b', old['paths'][0]['collection_id'])])

    def test_two_concurrent_writers_only_one_succeeds(self):
        initialize_ledger(self.ledger)
        data = snapshot()
        outcomes = []
        def attempt():
            try:
                outcomes.append(register_snapshot(data, self.ledger)['status'])
            except ValueError as exc:
                outcomes.append(str(exc).split(':')[0])
        threads = [threading.Thread(target=attempt) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertCountEqual(outcomes, ['ACCEPTED', 'REPLAY_DETECTED'])
        self.assertEqual(len(self.rows()), 1)

    def test_invalid_ledger_and_symlink_fail_closed(self):
        data = snapshot()
        self.ledger.write_text('not sqlite', encoding='utf-8')
        with self.assertRaises((sqlite3.DatabaseError, ValueError)):
            register_snapshot(data, self.ledger)
        self.ledger.unlink()
        initialize_ledger(self.ledger)
        link = self.root / 'link.sqlite'
        try:
            link.symlink_to(self.ledger)
        except (OSError, NotImplementedError):
            self.skipTest('Symlink unavailable on this platform')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            register_snapshot(data, link)

    def test_read_only_assessment_does_not_touch_ledger(self):
        data = snapshot()
        self.assertEqual(assess(data)['verified_active_paths'], 1)
        self.assertFalse(self.ledger.exists())

    def test_cli_init_register_and_replay_failure(self):
        script = Path(__file__).resolve().parents[1] / '03-Sources' / 'storagescope_windows.py'
        data = snapshot()
        input_file = self.root / 'input.json'
        input_file.write_text(json.dumps(data), encoding='utf-8')
        cmd = [sys.executable, str(script)]
        init = subprocess.run(cmd + ['--storage-replay-init', str(self.ledger)],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(init.returncode, 0, init.stderr)
        accepted = subprocess.run(cmd + ['--storage-replay-register', str(input_file), str(self.ledger)],
                                  capture_output=True, text=True, timeout=30)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(json.loads(accepted.stdout)['status'], 'ACCEPTED')
        replay = subprocess.run(cmd + ['--storage-replay-register', str(input_file), str(self.ledger)],
                                capture_output=True, text=True, timeout=30)
        self.assertNotEqual(replay.returncode, 0)
        self.assertNotIn(SECRET.hex(), replay.stderr)


if __name__ == '__main__':
    unittest.main()
