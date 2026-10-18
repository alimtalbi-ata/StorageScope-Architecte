"""Fail-closed pre-upgrade data backup gate. Author: Abdelhalim Talbi."""
import argparse
import json
from pathlib import Path
from upgrade_preflight_v580 import inspect_data_directory
from storagescope_windows import backup_snapshot, verify_backup_snapshot


def prepare_upgrade(data_dir, backup_dir):
    """Validate source, create distinct verified snapshot, or fail without touching source."""
    data = Path(data_dir).absolute()
    backup = Path(backup_dir).absolute()
    if data.is_symlink() or backup.is_symlink() or data == backup or data in backup.parents or backup in data.parents:
        raise ValueError('Unsafe data/backup directory relationship')
    result = inspect_data_directory(data)
    if not result['safe']:
        raise ValueError('Preflight failed: ' + ', '.join(result['findings']))
    if not data.is_dir():
        raise ValueError('No existing data to preserve')
    paths = {'base':data,'decisions':data/'architecture-decisions.sqlite',
             'campaigns':data/'campaigns.sqlite','views':data/'governance-views.json'}
    if not any(Path(paths[k]).is_file() for k in ('decisions','campaigns','views')):
        raise ValueError('No supported data files to back up')
    for key in ('decisions','campaigns','views'):
        path = paths[key]
        if path.is_symlink():
            raise ValueError('Symlinked data file: ' + path.name)
    folder, files = backup_snapshot(paths, backup)
    if not verify_backup_snapshot(folder):
        raise RuntimeError('Snapshot verification failed')
    return {'safe':True,'snapshot':str(folder),'files':[f.name for f in files], 'preflight':result}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--backup-dir', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare_upgrade(args.data_dir,args.backup_dir),ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({'safe':False,'error':str(exc)},ensure_ascii=False))
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
