#!/usr/bin/env python3
"""Recoverable Windows release publisher. Author: Abdelhalim Talbi.

A journal records intent BEFORE filesystem renames. Recovery is conservative:
missing backups for pre-existing targets cause a hard stop, never deletion.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

COMPONENTS = ('dist', 'installer', 'portable', 'build-logs')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def inventory(folder):
    return {str(p.relative_to(folder)).replace('\\', '/'): digest(p)
            for p in sorted(folder.rglob('*')) if p.is_file()}


def _sync_directory(folder):
    """Best-effort directory durability on POSIX; Windows directory fsync unavailable."""
    if os.name != 'posix':
        return
    flags = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0)
    fd = os.open(str(folder), flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _safe_dir(path):
    """Reject symlinked publication components (including dangling symlinks)."""
    return path.is_dir() and not path.is_symlink()


def _save(backup, state):
    temp = backup / 'journal.tmp'
    with temp.open('w', encoding='utf-8') as out:
        json.dump(state, out, indent=2)
        out.flush()
        os.fsync(out.fileno())
    os.replace(temp, backup / 'journal.json')
    _sync_directory(backup)


def recover(root):
    """Rollback a previously interrupted publication, preserving evidence on ambiguity."""
    root = Path(root)
    backup = root / '.publish-backup'
    journal = backup / 'journal.json'
    if backup.is_symlink() or journal.is_symlink():
        raise RuntimeError('Unsafe recovery journal or backup symlink')
    if not journal.is_file():
        raise RuntimeError('Recovery journal missing; manual inspection required')
    state = json.loads(journal.read_text(encoding='utf-8'))
    if state.get('schema') != 2 or state.get('phase') not in ('publishing', 'rollback_incomplete', 'complete'):
        raise RuntimeError('Unsupported or completed recovery journal; manual inspection required')
    items = state.get('items')
    if not isinstance(items, dict) or not items or set(items) - set(COMPONENTS):
        raise RuntimeError('Invalid recovery journal')
    # A crash after committing all artifacts but before removing the backup is
    # not a failed publication. Verify the committed payload before cleanup.
    if state['phase'] == 'complete':
        for name, item in items.items():
            target = root / name
            if (not isinstance(item, dict) or not isinstance(item.get('new_inventory'), dict)
                    or not _safe_dir(target) or inventory(target) != item['new_inventory']):
                raise RuntimeError(f'Committed publication mismatch for {name}; manual inspection required')
        shutil.rmtree(backup)
        _sync_directory(root)
        return
    # Preflight all components before changing anything. If an old target existed,
    # its backup MUST exist; otherwise the state is ambiguous and we fail closed.
    for name, item in items.items():
        if not isinstance(item, dict) or type(item.get('had_target')) is not bool:
            raise RuntimeError('Invalid journal component')
        target, previous = root / name, backup / name
        if previous.is_symlink() or target.is_symlink():
            raise RuntimeError(f'Symlinked publication component: {name}')
        if previous.exists() and (not _safe_dir(previous) or inventory(previous) != item.get('old_inventory')):
            raise RuntimeError(f'Corrupted backup for {name}; manual inspection required')
        if item['had_target'] and not previous.is_dir():
            if not target.is_dir() or inventory(target) != item.get('old_inventory'):
                raise RuntimeError(f'Backup absent for {name}; manual inspection required')
        if target.exists() and not _safe_dir(target):
            raise RuntimeError(f'Unexpected target type: {name}')
    try:
        for name, item in reversed(list(items.items())):
            target, previous = root / name, backup / name
            if item['had_target'] and not previous.exists():
                continue  # original target untouched
            if target.exists():
                shutil.rmtree(target)
            if item['had_target']:
                previous.rename(target)
        state['phase'] = 'rolled_back'
        _save(backup, state)
        shutil.rmtree(backup)
    except Exception as exc:
        state['phase'] = 'rollback_incomplete'
        state['error'] = str(exc)
        _save(backup, state)
        raise RuntimeError(f'ROLLBACK INCOMPLETE: {exc}') from exc


def publish(root, pending, fail_after=None, crash_after=None, crash_after_commit=False, crash_during_cleanup=False):
    """Publish staged directories; crash_after simulates abrupt exit for tests."""
    root, pending = Path(root), Path(pending)
    root_real, pending_real = root.resolve(), pending.resolve()
    # The native build deliberately stages in root/.publish-pending. Permit
    # ONLY this direct, named child; reject all other nested/overlapping paths.
    internal_pending = (pending_real.parent == root_real
                        and pending.name == '.publish-pending'
                        and not pending.is_symlink())
    if (root_real == pending_real or pending_real in root_real.parents
            or (root_real in pending_real.parents and not internal_pending)):
        raise ValueError('Publication and staging must be separate directories')
    backup = root / '.publish-backup'
    if backup.exists():
        raise RuntimeError('Unresolved .publish-backup; run explicit recovery')
    if not _safe_dir(pending) or root.is_symlink():
        raise ValueError('Missing staging directory')
    staged_names = [name for name in COMPONENTS if (pending / name).is_dir()]
    if not staged_names:
        raise ValueError('No staged publication directories')
    for name in staged_names:
        if not _safe_dir(pending / name):
            raise ValueError(f'Unsafe staged directory: {name}')
        if not inventory(pending / name):
            raise ValueError(f'Empty staged directory: {name}')
        if (root / name).is_symlink() or ((root / name).exists() and not _safe_dir(root / name)):
            raise ValueError(f'Unexpected published target: {name}')
    # Nested staging must contain only the four declared components, never
    # user data, stray files or a symlinked sidecar.
    if internal_pending and {p.name for p in pending.iterdir()} != set(staged_names):
        raise ValueError('Unexpected nested staging contents')
    backup.mkdir()
    _sync_directory(root)
    state = {'schema': 2, 'phase': 'publishing',
             'items': {name: {'had_target': (root / name).exists(),
                              'old_inventory': inventory(root / name) if (root / name).exists() else None,
                              'new_inventory': inventory(pending / name)}
                       for name in staged_names}}
    _save(backup, state)
    steps = 0
    try:
        for name in staged_names:
            target, previous, staged = root / name, backup / name, pending / name
            if state['items'][name]['had_target']:
                target.rename(previous)
                _sync_directory(root)
                _sync_directory(backup)
                steps += 1
                if crash_after == steps: raise SystemExit('SIMULATED_CRASH')
                if fail_after == steps: raise RuntimeError('INJECTED_FAILURE')
            staged.rename(target)
            _sync_directory(root)
            _sync_directory(pending)
            steps += 1
            if crash_after == steps: raise SystemExit('SIMULATED_CRASH')
            if fail_after == steps: raise RuntimeError('INJECTED_FAILURE')
        state['phase'] = 'complete'
        _save(backup, state)
        if crash_after_commit:
            raise SystemExit('SIMULATED_CRASH_AFTER_COMMIT')
        if crash_during_cleanup:
            # Simulate interruption after removing one old artifact but before
            # deleting the durable commit journal.
            for name in staged_names:
                old = backup / name
                if old.exists():
                    shutil.rmtree(old)
                    break
            raise SystemExit('SIMULATED_CRASH_DURING_CLEANUP')
        if internal_pending:
            pending.rmdir()  # remove only the now-empty internal staging dir
        shutil.rmtree(backup)
        _sync_directory(root)
    except Exception:
        recover(root)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--pending')
    parser.add_argument('--recover', action='store_true')
    args = parser.parse_args()
    if args.recover:
        recover(args.root)
    elif args.pending:
        publish(args.root, args.pending)
    else:
        parser.error('--pending is required unless --recover is set')


if __name__ == '__main__':
    main()
