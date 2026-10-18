"""Conservative, manual recovery to a NEW empty directory. Author: Abdelhalim Talbi."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sqlite3
from contextlib import closing
from storagescope_windows import verify_backup_snapshot

ALLOWED = {'architecture-decisions.sqlite', 'campaigns.sqlite', 'governance-views.json'}

def restore_to_empty(snapshot, destination):
    """Verify source and stage copies; never replace existing destination or files."""
    source = Path(snapshot).absolute()
    target = Path(destination).absolute()
    if source.is_symlink() or target.is_symlink() or source == target or source in target.parents or target in source.parents:
        raise ValueError('Unsafe source/destination relationship')
    if not source.is_dir() or not verify_backup_snapshot(source):
        raise ValueError('Snapshot integrity check failed')
    manifest = json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    names = [entry['name'] for entry in manifest['files']]
    if any(name not in ALLOWED for name in names):
        raise ValueError('Unknown snapshot file')
    for name in names:
        if (source/name).is_symlink():
            raise ValueError('Symlinked snapshot file')
        if name.endswith('.sqlite'):
            with closing(sqlite3.connect((source/name).as_uri()+'?mode=ro',uri=True)) as db:
                if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                    raise ValueError('Invalid SQLite backup: '+name)
    # Exclusive creation ensures an existing destination is never touched.
    target.mkdir(parents=True, exist_ok=False)
    try:
        for name in names:
            with (source/name).open('rb') as reader, (target/name).open('xb') as writer:
                shutil.copyfileobj(reader,writer)
                writer.flush()
                os.fsync(writer.fileno())
        if not all((target/name).stat().st_size == (source/name).stat().st_size for name in names):
            raise RuntimeError('Incomplete copy')
        return {'restored':True,'destination':str(target),'files':names}
    except Exception:
        shutil.rmtree(target)
        raise

def main():
    parser=argparse.ArgumentParser(description='Restore verified snapshot into a NEW directory only')
    parser.add_argument('--snapshot',required=True)
    parser.add_argument('--destination',required=True)
    args=parser.parse_args()
    try:
        print(json.dumps(restore_to_empty(args.snapshot,args.destination),ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({'restored':False,'error':str(exc)},ensure_ascii=False))
        return 1

if __name__=='__main__':
    raise SystemExit(main())
