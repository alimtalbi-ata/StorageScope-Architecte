"""V6.230 frozen Windows manufacturer collision qualification.
Only synthetic snapshots; no CMDB writes. Author: Abdelhalim Talbi.
"""
import argparse
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory


def run(executable):
    with TemporaryDirectory(prefix='storagescope-v6230-') as temp:
        root = Path(temp)

        def review(records, name):
            source = root / (name + '.json')
            output = root / (name + '-report.json')
            source.write_text(json.dumps(records), encoding='utf-8')
            process = subprocess.run([str(executable), '--cmdb-review-file', str(source), str(output)],
                                     capture_output=True, text=True, timeout=120)
            if process.returncode != 0 or not output.is_file():
                raise AssertionError(f'Frozen CMDB {name} failed: {process.stderr[:400]}')
            report = json.loads(output.read_text(encoding='utf-8'))
            if report.get('automatic_merges') != 0 or report.get('destructive_changes') != 0:
                raise AssertionError('Frozen CMDB made unauthorized changes')
            return report

        conflict = review([{'source': 'CMDB', 'serial': 'S1', 'manufacturer': 'NetApp'},
                           {'source': 'collector', 'serial': 'S1', 'vendor': 'Pure Storage'},
                           {'source': 'other', 'serial': 'S1'}], 'manufacturer-conflict')
        if (conflict['assessment'] != 'INCOMPLETE' or
                conflict['quarantined_indices'] != [0, 1, 2] or
                not any(c['action'] == 'QUARANTINE_IDENTITY_CONFLICT' and
                        any(x['field'] == 'manufacturer' for x in c['identity_conflicts'])
                        for c in conflict['candidates'])):
            raise AssertionError('Frozen CMDB did not quarantine manufacturer collision')
        valid = review([{'source': 'CMDB', 'serial': 'S1', 'vendor': 'PURE STORAGE'},
                        {'source': 'collector', 'serial': 's1', 'manufacturer': 'pure storage'}], 'same-vendor')
        if valid['assessment'] != 'REVIEW_REQUIRED' or valid['quarantined_indices']:
            raise AssertionError('Frozen CMDB quarantined compatible manufacturer evidence')
        invalid = review([{'source': 'CMDB', 'serial': 'S1', 'vendor': 'IBM', 'manufacturer': 'HPE'},
                          {'source': 'collector', 'serial': 'S1'}], 'self-conflict')
        if (invalid['invalid_records'] != [{'index': 0, 'reason': 'conflicting_manufacturer'}] or
                invalid['candidate_count'] != 0):
            raise AssertionError('Frozen CMDB trusted internally contradictory manufacturer')
    print('Frozen V6.230 CMDB manufacturer identity quarantine PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=Path, required=True)
    args = parser.parse_args()
    if not args.exe.is_file():
        parser.error('Frozen Windows executable missing')
    run(args.exe.resolve())
