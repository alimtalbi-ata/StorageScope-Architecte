"""Conservative, manual recovery to a NEW empty directory. Author: Abdelhalim Talbi."""
import argparse
import hashlib
import tempfile
import json
import os
from pathlib import Path
import shutil
import sqlite3
import time
import stat
from contextlib import closing
from storagescope_windows import verify_backup_snapshot

ALLOWED = {'architecture-decisions.sqlite', 'campaigns.sqlite', 'governance-views.json'}

def inspect_interrupted_restores(parent, minimum_age_seconds=3600, now=None):
    """Read-only inventory of abandoned staging directories; no automatic deletion.

    Recent stages are never cleanup candidates because a restore may still be running.
    """
    parent = Path(parent)
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError('Parent must be an existing non-symlink directory')
    if type(minimum_age_seconds) not in (int, float) or minimum_age_seconds < 60:
        raise ValueError('Minimum age must be at least 60 seconds')
    timestamp = time.time() if now is None else now
    results = []
    for entry in sorted(parent.iterdir()):
        if not entry.name.startswith('.storagescope-restore-'):
            continue
        metadata = entry.lstat()
        if not stat.S_ISDIR(metadata.st_mode):
            results.append({'name':entry.name,'status':'UNSAFE_ENTRY'})
            continue
        age = max(0, timestamp - metadata.st_mtime)
        # No deletion is offered: stage ownership and liveness cannot be established
        # reliably after a crash, especially on shared network storage.
        results.append({'name':entry.name, 'status':'REVIEW_OLD' if age >= minimum_age_seconds else 'RECENT',
                        'age_seconds':round(age)})
    return {'parent':str(parent.absolute()), 'stages':results, 'deleted':0}


def publish_verified_interrupted_stage(stage_path, snapshot, destination):
    """Manual resume: verify stage against trusted snapshot, publish to NEW path only.

    Does not mutate or delete stage on failure. Operator must choose the exact stage.
    """
    stage = Path(stage_path).absolute()
    source = Path(snapshot).absolute()
    target = Path(destination).absolute()
    if any(p.is_symlink() for p in (stage, source, target, target.parent)):
        raise ValueError('Symlink in recovery path')
    if (not stage.name.startswith('.storagescope-restore-') or
            not stage.is_dir() or not source.is_dir() or not target.parent.is_dir()):
        raise ValueError('Invalid recovery paths')
    if stage.parent != target.parent or target.exists() or target.is_symlink():
        raise FileExistsError('Destination must be absent and a sibling of stage')
    if source == stage or source == target or source in target.parents or target in source.parents:
        raise ValueError('Unsafe snapshot/destination relationship')
    if not verify_backup_snapshot(source):
        raise ValueError('Invalid source snapshot')
    manifest = json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    expected = {item['name']:item for item in manifest['files']}
    if not expected or any(name not in ALLOWED for name in expected):
        raise ValueError('Unexpected snapshot file')
    actual = {entry.name for entry in stage.iterdir()}
    if actual != set(expected):
        raise ValueError('Incomplete or unexpected staged files')
    for name, entry in expected.items():
        f = stage/name
        if not f.is_file() or f.is_symlink():
            raise ValueError('Unsafe staged file')
        digest = hashlib.sha256()
        count = 0
        with f.open('rb') as reader:
            for block in iter(lambda:reader.read(1024*1024), b''):
                digest.update(block)
                count += len(block)
        if count != entry['bytes'] or digest.hexdigest() != entry['sha256']:
            raise ValueError('Corrupt staged file: '+name)
        if name.endswith('.sqlite'):
            with closing(sqlite3.connect(f.as_uri()+'?mode=ro',uri=True)) as db:
                if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                    raise ValueError('Invalid staged SQLite: '+name)
    if not verify_backup_snapshot(source) or target.exists():
        raise ValueError('Snapshot changed or destination appeared')
    stage.rename(target)
    return {'resumed':True,'destination':str(target),'files':sorted(expected)}

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
    # Stage in a private sibling directory; publish only after every byte is checked.
    if not target.parent.is_dir() or target.exists() or target.is_symlink():
        raise FileExistsError('Destination must not exist and parent must exist')
    if target.parent.is_symlink():
        raise ValueError('Symlinked destination parent')
    stage = Path(tempfile.mkdtemp(prefix='.storagescope-restore-', dir=target.parent))
    try:
        for entry in manifest['files']:
            name = entry['name']
            digest = hashlib.sha256()
            count = 0
            with (source/name).open('rb') as reader, (stage/name).open('xb') as writer:
                while True:
                    chunk = reader.read(1024 * 1024)
                    if not chunk:
                        break
                    writer.write(chunk)
                    digest.update(chunk)
                    count += len(chunk)
                writer.flush()
                os.fsync(writer.fileno())
            if count != entry['bytes'] or digest.hexdigest() != entry['sha256']:
                raise ValueError('Snapshot changed during restore: ' + name)
        # Detect source mutation between preflight and publication.
        if not verify_backup_snapshot(source):
            raise ValueError('Snapshot changed before publication')
        if target.exists() or target.is_symlink():
            raise FileExistsError('Destination appeared during restore')
        stage.rename(target)
        return {'restored': True, 'destination': str(target), 'files': names}
    finally:
        if stage.exists():
            shutil.rmtree(stage)

def main():
    parser=argparse.ArgumentParser(description='Restore verified snapshot into a NEW directory only')
    parser.add_argument('--snapshot',required=True)
    parser.add_argument('--resume-stage',help='Manually resume a verified interrupted stage')
    parser.add_argument('--destination',required=True)
    args=parser.parse_args()
    try:
        print(json.dumps(publish_verified_interrupted_stage(args.resume_stage,args.snapshot,args.destination) if args.resume_stage else restore_to_empty(args.snapshot,args.destination),ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({'restored':False,'error':str(exc)},ensure_ascii=False))
        return 1

if __name__=='__main__':
    raise SystemExit(main())
