"""V6.224 native Windows audit fail-closed check; synthetic SQLite fixtures only.
Author: Abdelhalim Talbi.
"""
import argparse
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import subprocess
from tempfile import TemporaryDirectory
from uuid import uuid4


def run(executable):
    with TemporaryDirectory(prefix='storagescope-v6224-audit-') as temporary:
        ledger = Path(temporary) / 'ledger.sqlite'
        result = subprocess.run([str(executable), '--storage-replay-init', str(ledger)],
                                capture_output=True, text=True, timeout=120)
        if result.returncode:
            raise AssertionError('Frozen ledger initialization failed: ' + result.stderr)
        with closing(sqlite3.connect(ledger)) as db:
            with db:
                for stamp in ('2026-10-24T00:00:00+00:00',
                              '2026-10-24T12:00:00+00:00INVALID',
                              '2026-10-24T23:59:59+00:00'):
                    db.execute('INSERT INTO collection_seen VALUES (?, ?, ?, ?)',
                               ('collector:a', str(uuid4()), 1, stamp))
        before = hashlib.sha256(ledger.read_bytes()).hexdigest()
        result = subprocess.run([str(executable), '--storage-replay-audit', str(ledger)],
                                capture_output=True, text=True, timeout=120)
        if result.returncode == 0 or 'invalid UTC timestamp' not in result.stderr:
            raise AssertionError('Frozen audit accepted malformed interior timestamp')
        if hashlib.sha256(ledger.read_bytes()).hexdigest() != before:
            raise AssertionError('Frozen audit modified the ledger')
        moved = ledger.with_name('moved.sqlite')
        ledger.rename(moved)
        moved.rename(ledger)
    print('Frozen V6.224 full-row audit validation PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=Path, required=True)
    args = parser.parse_args()
    if not args.exe.is_file():
        parser.error('Frozen executable missing')
    run(args.exe.resolve())
