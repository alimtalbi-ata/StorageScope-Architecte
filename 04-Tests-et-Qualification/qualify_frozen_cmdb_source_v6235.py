"""V6.235 frozen Windows CMDB collector provenance quarantine.

Synthetic read-only evidence; never writes to CMDB. Author: Abdelhalim Talbi.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory


def run(executable):
    with TemporaryDirectory(prefix='storagescope-v6235-') as temp:
        root = Path(temp)
        source = root / 'spoofed-collector.json'
        destination = root / 'review.json'
        records = [{'source': 'CMDB', 'serial': 'S1'},
                   {'source': 'ＣＭＤＢ', 'serial': 's1'},
                   {'source': 'collector\u200bhidden', 'serial': 'S2'},
                   {'source': 'cmdb', 'serial': 's2'},
                   {'source': 'probe', 'serial': 'S2'},
                   {'source': 'cmdb', 'serial': 'SAFE'},
                   {'source': 'probe', 'serial': 'safe'}]
        raw = json.dumps(records, ensure_ascii=False).encode('utf-8')
        source.write_bytes(raw)
        process = subprocess.run([str(executable), '--cmdb-review-file', str(source), str(destination)],
                                 capture_output=True, text=True, timeout=120)
        if process.returncode != 0 or not destination.is_file():
            raise AssertionError(f'Frozen CMDB collector review failed: {process.stderr[:400]}')
        report = json.loads(destination.read_text(encoding='utf-8'))
        if (report['candidate_count'] != 3 or
                report['invalid_records'] != [{'index': 2, 'reason': 'invalid_source'}] or
                report['duplicate_source_indices'] != [0, 1] or
                report['invalid_identity_link_indices'] != [3, 4] or
                report['quarantined_indices'] != [0, 1, 3, 4] or
                [c['action'] for c in report['candidates']] != [
                    'QUARANTINE_DUPLICATE_SOURCE_OBSERVATION',
                    'QUARANTINE_LINKED_INVALID_RECORD', 'REVIEW_REQUIRED'] or
                report['snapshot_sha256'] != hashlib.sha256(raw).hexdigest() or
                report['automatic_merges'] != 0 or report['destructive_changes'] != 0 or
                source.read_bytes() != raw):
            raise AssertionError('Frozen V6.235 collector provenance quarantine contract failed')
    print('Frozen V6.235 CMDB collector provenance qualification PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=Path, required=True)
    args = parser.parse_args()
    if not args.exe.is_file():
        parser.error('Frozen Windows executable missing')
    run(args.exe.resolve())
