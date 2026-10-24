"""V6.223 frozen Windows read-only ledger audit qualification; synthetic only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory


def run(executable):
    with TemporaryDirectory(prefix='storagescope-v6223-audit-') as tmp:
        ledger = Path(tmp) / 'replay.sqlite'
        def invoke(*args):
            return subprocess.run([str(executable), *map(str, args)],
                                  capture_output=True, text=True, timeout=120)
        missing = invoke('--storage-replay-audit', ledger)
        if missing.returncode == 0 or ledger.exists():
            raise AssertionError('Frozen audit silently initialized a missing ledger')
        init = invoke('--storage-replay-init', ledger)
        if init.returncode != 0:
            raise AssertionError('Frozen ledger init failed')
        before = hashlib.sha256(ledger.read_bytes()).hexdigest()
        audit = invoke('--storage-replay-audit', ledger)
        if audit.returncode != 0:
            raise AssertionError('Frozen read-only audit failed: ' + audit.stderr)
        report = json.loads(audit.stdout)
        if (report.get('schema') != 'storagescope.replay-ledger-audit.v1'
                or report.get('integrity') != 'PASS'
                or report.get('registered_collections') != 0
                or report.get('automatic_changes') != 0):
            raise AssertionError('Frozen audit output contract invalid')
        if hashlib.sha256(ledger.read_bytes()).hexdigest() != before:
            raise AssertionError('Frozen audit modified SQLite ledger')
    print('Frozen V6.223 read-only replay ledger audit PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=Path, required=True)
    args = parser.parse_args()
    if not args.exe.is_file():
        parser.error('Frozen executable missing')
    run(args.exe.resolve())
