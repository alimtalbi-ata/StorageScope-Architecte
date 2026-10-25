"""V6.233 frozen Windows transitive duplicate-source CMDB qualification.
Synthetic, read-only. Author: Abdelhalim Talbi.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory


def run(executable):
    with TemporaryDirectory(prefix='storagescope-v6233-') as temp:
        root = Path(temp)
        source = root / 'transitive-source.json'
        destination = root / 'report.json'
        records = [{'source': 'cmdb', 'serial': 'S1'},
                   {'source': 'probe', 'serial': 'S1', 'uuid': 'U2'},
                   {'source': 'CMDB', 'uuid': 'U2'}]
        raw = json.dumps(records).encode('utf-8')
        source.write_bytes(raw)
        result = subprocess.run([str(executable), '--cmdb-review-file', str(source), str(destination)],
                                capture_output=True, text=True, timeout=120)
        if result.returncode != 0 or not destination.is_file():
            raise AssertionError(f'Frozen CMDB transitive review failed: {result.stderr[:400]}')
        report = json.loads(destination.read_text(encoding='utf-8'))
        if (report['candidate_count'] != 2 or
                report['duplicate_source_indices'] != [0, 2] or
                report['transitive_duplicate_source_indices'] != [0, 2] or
                report['quarantined_indices'] != [0, 1, 2] or
                any(candidate['action'] != 'QUARANTINE_LINKED_DUPLICATE_SOURCE_OBSERVATION'
                    for candidate in report['candidates']) or
                report['snapshot_sha256'] != hashlib.sha256(raw).hexdigest() or
                report['automatic_merges'] != 0 or report['destructive_changes'] != 0 or
                source.read_bytes() != raw):
            raise AssertionError('Frozen V6.233 transitive source quarantine/evidence integrity failed')
    print('Frozen V6.233 transitive CMDB source qualification PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=Path, required=True)
    args = parser.parse_args()
    if not args.exe.is_file():
        parser.error('Frozen Windows executable missing')
    run(args.exe.resolve())
