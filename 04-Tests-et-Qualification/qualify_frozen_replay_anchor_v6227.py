"""V6.227 native executable regression: reject nested ledger-domain checkpoints.
Synthetic fixtures only. Author: Abdelhalim Talbi.
"""
import argparse
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory


def run(executable):
    with TemporaryDirectory(prefix='storagescope-v6227-') as temp:
        root = Path(temp)
        ledger_dir = root / 'ledger'
        ledger_dir.mkdir()
        protected = root / 'protected'
        protected.mkdir()
        nested = ledger_dir / 'backups'
        nested.mkdir()
        ledger = ledger_dir / 'replay.sqlite'
        good = protected / 'checkpoint.json'
        bad = nested / 'checkpoint.json'
        env = os.environ.copy()
        env['STORAGESCOPE_REPLAY_ANCHOR_KEY'] = bytes(range(32)).hex()

        def call(*args):
            return subprocess.run([str(executable), *map(str, args)], env=env,
                                  capture_output=True, text=True, timeout=120)

        if call('--storage-replay-init', ledger).returncode:
            raise AssertionError('Frozen V6.227 ledger initialization failed')
        if call('--storage-replay-anchor-create', ledger, good).returncode:
            raise AssertionError('Frozen V6.227 valid anchor creation failed')
        if call('--storage-replay-anchor-check', ledger, good).returncode:
            raise AssertionError('Frozen V6.227 valid independent anchor rejected')
        if call('--storage-replay-anchor-create', ledger, bad).returncode == 0 or bad.exists():
            raise AssertionError('Frozen V6.227 nested anchor created inside ledger restore domain')
        bad.write_bytes(good.read_bytes())
        if call('--storage-replay-anchor-check', ledger, bad).returncode == 0:
            raise AssertionError('Frozen V6.227 nested anchor verified inside ledger restore domain')
        bad.unlink()
        traversal = protected / '..' / 'ledger' / 'backups' / 'checkpoint.json'
        if call('--storage-replay-anchor-create', ledger, traversal).returncode == 0 or bad.exists():
            raise AssertionError('Frozen V6.227 path traversal bypassed anchor containment')
        if call('--storage-replay-anchor-check', ledger, good).returncode:
            raise AssertionError('Frozen V6.227 independent checkpoint stopped working')
    print('Frozen V6.227 ledger-directory subtree isolation PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=Path, required=True)
    args = parser.parse_args()
    if not args.exe.is_file():
        parser.error('Frozen executable missing')
    run(args.exe.resolve())
