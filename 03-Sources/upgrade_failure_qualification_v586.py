"""Safe, isolated negative-path qualification for the upgrade gate. Abdelhalim Talbi."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
from contextlib import closing
import tempfile
from upgrade_gate_v581 import prepare_upgrade


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def qualify():
    cases = []
    with tempfile.TemporaryDirectory(prefix='ss-upgrade-negative-') as temp:
        root = Path(temp)
        for name in ('corrupt_sqlite', 'unsafe_backup_location', 'no_supported_data', 'valid_data'):
            data = root / name / 'data'
            data.mkdir(parents=True)
            backup = root / name / 'backups'
            if name == 'corrupt_sqlite':
                (data / 'campaigns.sqlite').write_bytes(b'not a sqlite database')
            elif name == 'valid_data':
                with closing(sqlite3.connect(data / 'campaigns.sqlite')) as db, db:
                    db.execute('CREATE TABLE evidence (id INTEGER PRIMARY KEY, value TEXT)')
                    db.execute('INSERT INTO evidence(value) VALUES (?)', ('preserved',))
            elif name == 'unsafe_backup_location':
                (data / 'governance-views.json').write_text('{}', encoding='utf-8')
                backup = data / 'nested-backups'
            before = {p.name: _hash(p) for p in data.iterdir() if p.is_file()}
            error = None
            snapshot = None
            try:
                result = prepare_upgrade(data, backup)
                snapshot = Path(result['snapshot'])
            except (ValueError, RuntimeError, OSError, sqlite3.DatabaseError) as exc:
                error = type(exc).__name__
            after = {p.name: _hash(p) for p in data.iterdir() if p.is_file()}
            expected_success = name == 'valid_data'
            passed = (snapshot is not None) == expected_success and before == after
            if snapshot is not None:
                passed = passed and snapshot.is_dir() and (snapshot / 'manifest.json').exists()
            if not expected_success:
                passed = passed and not backup.exists()
            cases.append({'case': name, 'passed': bool(passed), 'blocked': snapshot is None,
                          'error_type': error, 'source_unchanged': before == after})
    return {'passed': all(c['passed'] for c in cases), 'cases': cases,
            'scope': 'isolated Python gate; does not launch Windows installer'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = qualify()
    content = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(content + '\n', encoding='utf-8')
    print(content)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
