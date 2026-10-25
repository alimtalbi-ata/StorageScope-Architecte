"""V6.231 frozen Windows strict CMDB strong-identity type qualification.
Synthetic read-only snapshots. Author: Abdelhalim Talbi.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory


def run(executable):
    with TemporaryDirectory(prefix='storagescope-v6231-') as temp:
        root = Path(temp)

        def review(records, name):
            source = root / (name + '.json')
            output = root / (name + '-report.json')
            raw = json.dumps(records, ensure_ascii=False).encode('utf-8')
            source.write_bytes(raw)
            process = subprocess.run([str(executable), '--cmdb-review-file', str(source), str(output)],
                                     capture_output=True, text=True, timeout=120)
            if process.returncode != 0 or not output.is_file():
                raise AssertionError(f'Frozen CMDB {name} failed: {process.stderr[:400]}')
            report = json.loads(output.read_text(encoding='utf-8'))
            if (report.get('automatic_merges') != 0 or report.get('destructive_changes') != 0 or
                    report.get('snapshot_sha256') != hashlib.sha256(raw).hexdigest() or
                    source.read_bytes() != raw):
                raise AssertionError('Frozen CMDB evidence integrity or read-only contract failed')
            return report

        malformed = review([{'source': 'CMDB', 'serial': 'S1', 'wwn': 123},
                            {'source': 'collector', 'serial': 'S1', 'wwn': '123'}], 'malformed-wwn')
        if (malformed['assessment'] != 'INCOMPLETE' or malformed['candidate_count'] != 0 or
                malformed['invalid_records'] != [{'index': 0, 'reason': 'invalid_identity_type:wwn'}]):
            raise AssertionError('Frozen CMDB accepted a malformed strong identifier')

        valid = review([{'source': 'CMDB', 'serial': 'S1', 'wwn': None},
                        {'source': 'collector', 'serial': 's1', 'wwn': 'N/A'}], 'unknown-wwn')
        if (valid['assessment'] != 'REVIEW_REQUIRED' or valid['candidate_count'] != 1 or
                valid['quarantined_indices']):
            raise AssertionError('Frozen CMDB rejected valid unknown strong identifiers')
    print('Frozen V6.231 CMDB strong identity type qualification PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=Path, required=True)
    args = parser.parse_args()
    if not args.exe.is_file():
        parser.error('Frozen Windows executable missing')
    run(args.exe.resolve())
