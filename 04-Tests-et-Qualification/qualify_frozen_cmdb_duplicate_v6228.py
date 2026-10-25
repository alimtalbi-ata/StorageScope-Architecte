"""V6.228 native Windows executable CMDB duplicate-source regression.
Synthetic local snapshots; no CMDB write. Author: Abdelhalim Talbi.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory


def run(executable):
    with TemporaryDirectory(prefix='storagescope-v6228-') as temp:
        root = Path(temp)

        def review(records, name):
            source = root / (name + '.json')
            output = root / (name + '-review.json')
            source.write_text(json.dumps(records, ensure_ascii=True), encoding='utf-8')
            process = subprocess.run([str(executable), '--cmdb-review-file', str(source), str(output)],
                                     capture_output=True, text=True, timeout=120,
                                     env=os.environ.copy())
            if process.returncode or not output.is_file():
                raise AssertionError(f'Frozen CMDB review {name} failed: {process.stderr[:400]}')
            result = json.loads(output.read_text(encoding='utf-8'))
            if result.get('automatic_merges') != 0 or result.get('destructive_changes') != 0:
                raise AssertionError('Frozen CMDB performed automatic changes')
            return result

        duplicate = review([{'source': 'NetApp', 'serial': 'S1'},
                            {'source': ' netapp ', 'serial': 's1'},
                            {'source': 'CMDB', 'serial': 'S1'}], 'duplicate')
        if (duplicate['assessment'] != 'INCOMPLETE' or
                duplicate.get('duplicate_source_indices') != [0, 1] or
                duplicate['quarantined_indices'] != [0, 1, 2] or
                duplicate['propagated_quarantine_indices'] != [2] or
                any(c['action'] == 'REVIEW_REQUIRED' for c in duplicate['candidates'])):
            raise AssertionError('Frozen CMDB duplicate-source quarantine missing')
        independent = review([{'source': 'NetApp', 'serial': 'S1'},
                              {'source': 'CMDB', 'serial': 's1'}], 'independent')
        if (independent['assessment'] != 'REVIEW_REQUIRED' or
                independent.get('duplicate_source_indices') != []):
            raise AssertionError('Frozen independent sources incorrectly quarantined')
    print('Frozen V6.228 CMDB same-source quarantine PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=Path, required=True)
    args = parser.parse_args()
    if not args.exe.is_file():
        parser.error('Frozen Windows executable missing')
    run(args.exe.resolve())
