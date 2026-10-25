"""V6.232 frozen Windows CMDB invalid identity quarantine.
Synthetic read-only snapshots. Author: Abdelhalim Talbi.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory


def run(executable):
    with TemporaryDirectory(prefix='storagescope-v6232-') as temp:
        root = Path(temp)
        source = root / 'invalid-linked.json'
        destination = root / 'report.json'
        records = [{'source': 'bad', 'serial': 'S1', 'uuid': [1]},
                   {'source': 'cmdb', 'serial': 's1', 'uuid': 'U1'},
                   {'source': 'array', 'uuid': 'u1'}]
        raw = json.dumps(records).encode('utf-8')
        source.write_bytes(raw)
        process = subprocess.run([str(executable), '--cmdb-review-file', str(source), str(destination)],
                                 capture_output=True, text=True, timeout=120)
        if process.returncode != 0 or not destination.is_file():
            raise AssertionError(f'Frozen CMDB review failed: {process.stderr[:400]}')
        report = json.loads(destination.read_text(encoding='utf-8'))
        if (report['candidate_count'] != 1 or
                report['candidates'][0]['action'] != 'QUARANTINE_LINKED_INVALID_RECORD' or
                report['invalid_identity_link_indices'] != [1] or
                report['quarantined_indices'] != [1, 2] or
                report['snapshot_sha256'] != hashlib.sha256(raw).hexdigest() or
                report['automatic_merges'] != 0 or report['destructive_changes'] != 0 or
                source.read_bytes() != raw):
            raise AssertionError('Frozen V6.232 invalid identity quarantine or evidence integrity failed')
    print('Frozen V6.232 CMDB invalid identity link qualification PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=Path, required=True)
    args = parser.parse_args()
    if not args.exe.is_file():
        parser.error('Frozen Windows executable missing')
    run(args.exe.resolve())
