"""Frozen V6.226 replay-anchor hardening qualification, synthetic fixtures.
Author: Abdelhalim Talbi.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory


def run(executable):
    with TemporaryDirectory(prefix='storagescope-v6226-') as temp:
        root = Path(temp)
        (root / 'ledger').mkdir()
        (root / 'protected').mkdir()
        ledger = root / 'ledger' / 'replay.sqlite'
        anchor = root / 'protected' / 'checkpoint.json'
        env = os.environ.copy()
        env['STORAGESCOPE_REPLAY_ANCHOR_KEY'] = bytes(range(32)).hex()

        def call(*args):
            return subprocess.run([str(executable), *map(str, args)], env=env,
                                  capture_output=True, text=True, timeout=120)

        if call('--storage-replay-init', ledger).returncode:
            raise AssertionError('Frozen ledger initialization failed')
        if call('--storage-replay-anchor-create', ledger, anchor).returncode:
            raise AssertionError('Frozen checkpoint creation failed')
        if call('--storage-replay-anchor-check', ledger, anchor).returncode:
            raise AssertionError('Frozen valid checkpoint rejected')
        original = anchor.read_bytes()
        anchor.write_text(json.dumps(json.loads(original), indent=2) + '\n', encoding='ascii')
        if call('--storage-replay-anchor-check', ledger, anchor).returncode == 0:
            raise AssertionError('Frozen noncanonical JSON accepted')
        anchor.write_bytes(b'{"schema":"storagescope.replay-anchor.v1",' + original[1:])
        if call('--storage-replay-anchor-check', ledger, anchor).returncode == 0:
            raise AssertionError('Frozen duplicate JSON keys accepted')
        anchor.write_bytes(original)
        hardlink = anchor.with_name('hardlink.json')
        try:
            os.link(anchor, hardlink)
        except (OSError, NotImplementedError):
            print('Hardlink gate unavailable on this filesystem: SKIPPED')
        else:
            if call('--storage-replay-anchor-check', ledger, anchor).returncode == 0:
                raise AssertionError('Frozen hardlinked anchor accepted')
            hardlink.unlink()
        if call('--storage-replay-anchor-check', ledger, anchor).returncode:
            raise AssertionError('Frozen canonical checkpoint not restored')
    print('Frozen V6.226 anchor hardening PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=Path, required=True)
    args = parser.parse_args()
    if not args.exe.is_file():
        parser.error('Frozen executable missing')
    run(args.exe.resolve())
