"""Non-destructive upgrade interruption rehearsal. Author: Abdelhalim Talbi."""
from pathlib import Path
import hashlib
import json
import tempfile
from unittest.mock import patch
import shutil
from upgrade_gate_v581 import prepare_upgrade
from snapshot_restore_v583 import restore_to_empty

def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def rehearse(data_dir, backup_dir):
    """Back up live data, simulate interrupted recovery copy, verify no live data changed.

    No installer is launched. This validates recovery behavior only, not Windows setup.
    """
    data = Path(data_dir).absolute()
    backup = Path(backup_dir).absolute()
    if not data.is_dir():
        raise ValueError('Data directory missing')
    tracked = [p for p in data.iterdir() if p.is_file() and p.name in
               ('architecture-decisions.sqlite','campaigns.sqlite','governance-views.json')]
    if not tracked:
        raise ValueError('No supported data')
    before = {p.name:_digest(p) for p in tracked}
    prepared = prepare_upgrade(data, backup)
    snapshot = Path(prepared['snapshot'])
    # Temporary parent is outside the live data and snapshot; restore target must be new.
    with tempfile.TemporaryDirectory(prefix='storagescope-interruption-') as scratch:
        interrupted = Path(scratch)/'interrupted'
        def fail_copy(*args, **kwargs):
            raise OSError('INJECTED_COPY_FAILURE')
        try:
            with patch('snapshot_restore_v583.os.fsync', side_effect=fail_copy):
                restore_to_empty(snapshot, interrupted)
        except OSError as exc:
            if str(exc) != 'INJECTED_COPY_FAILURE':
                raise
        else:
            raise AssertionError('Fault injection did not interrupt restore')
        if interrupted.exists():
            raise AssertionError('Partial restoration was not cleaned')
        recovered = Path(scratch)/'recovered'
        result = restore_to_empty(snapshot, recovered)
        if not result['restored']:
            raise AssertionError('Recovery failed')
        if any(_digest(recovered/name) != digest for name,digest in before.items()):
            raise AssertionError('Recovered content differs')
    if any(_digest(data/name) != digest for name,digest in before.items()):
        raise AssertionError('Live data changed during rehearsal')
    return {'passed':True,'snapshot':str(snapshot),'injected_failure':'INJECTED_COPY_FAILURE',
            'partial_target_removed':True,'recovered_verified':True,'live_data_unchanged':True}
