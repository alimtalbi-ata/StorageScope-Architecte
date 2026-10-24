"""V6.225 Windows frozen checkpoint gate using synthetic data only.
Author: Abdelhalim Talbi.
"""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from tempfile import TemporaryDirectory
from uuid import uuid4


def run(executable):
    with TemporaryDirectory(prefix='storagescope-v6225-anchor-') as temporary:
        root = Path(temporary)
        ledger_dir, anchor_dir = root / 'ledger', root / 'protected'
        ledger_dir.mkdir()
        anchor_dir.mkdir()
        ledger = ledger_dir / 'replay.sqlite'
        anchor = anchor_dir / 'checkpoint.json'
        env = os.environ.copy()
        env['STORAGESCOPE_REPLAY_ANCHOR_KEY'] = bytes(range(32)).hex()

        def call(*args):
            return subprocess.run([str(executable), *map(str, args)], env=env,
                                  capture_output=True, text=True, timeout=120)

        initialized = call('--storage-replay-init', ledger)
        if initialized.returncode:
            raise AssertionError('Frozen ledger init failed: ' + initialized.stderr)
        with closing(sqlite3.connect(ledger)) as db:
            with db:
                db.execute('INSERT INTO collection_seen VALUES (?, ?, ?, ?)',
                           ('synthetic:collector', str(uuid4()), 1,
                            '2026-10-25T00:00:00+00:00'))
        before = hashlib.sha256(ledger.read_bytes()).hexdigest()
        created = call('--storage-replay-anchor-create', ledger, anchor)
        if created.returncode or json.loads(created.stdout)['status'] != 'ANCHOR_CREATED':
            raise AssertionError('Frozen anchor creation failed: ' + created.stderr)
        checked = call('--storage-replay-anchor-check', ledger, anchor)
        if checked.returncode or json.loads(checked.stdout)['integrity'] != 'PASS':
            raise AssertionError('Frozen anchor verification failed: ' + checked.stderr)
        if hashlib.sha256(ledger.read_bytes()).hexdigest() != before:
            raise AssertionError('Frozen checkpoint modified ledger')
        with closing(sqlite3.connect(ledger)) as db:
            with db:
                db.execute('UPDATE collection_seen SET observation_count=2')
        rejected = call('--storage-replay-anchor-check', ledger, anchor)
        if rejected.returncode == 0 or 'ROLLBACK_OR_TAMPERING' not in rejected.stderr:
            raise AssertionError('Frozen anchor accepted changed ledger')
        if call('--storage-replay-anchor-create', ledger, anchor).returncode == 0:
            raise AssertionError('Frozen anchor overwrote existing checkpoint')
        moved = ledger.with_name('moved.sqlite')
        ledger.rename(moved)
        moved.rename(ledger)
    print('Frozen V6.225 replay anchor verification PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=Path, required=True)
    args = parser.parse_args()
    if not args.exe.is_file():
        parser.error('Frozen executable missing')
    run(args.exe.resolve())
