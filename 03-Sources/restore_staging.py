"""Conservative snapshot restore preparation. Author: Abdelhalim Talbi.

This module deliberately never overwrites active application files.
"""
from __future__ import annotations
import os
import shutil
import tempfile
from pathlib import Path
from storagescope_windows import verify_backup_snapshot, application_paths

ALLOWED = {
    "campaigns.sqlite": "campaigns",
    "architecture-decisions.sqlite": "decisions",
    "governance-views.json": "views",
}

def stage_verified_restore(snapshot, data_root, *, confirm=False):
    """Verify then stage into a new sibling directory; return staging path.

    No live file replacement occurs. A separate, tested activation protocol
    with process quiescence and rollback is required before production use.
    """
    if not confirm:
        raise PermissionError("Explicit restore staging confirmation required")
    source = Path(snapshot).resolve(strict=True)
    target = Path(data_root).resolve()
    if source == target or source in target.parents or target in source.parents:
        raise ValueError("Snapshot and active data must be separate")
    if not verify_backup_snapshot(source):
        raise ValueError("Snapshot verification failed")
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="storagescope-restore-", dir=target.parent))
    try:
        for filename in ALLOWED:
            file = source / filename
            if not file.exists():
                continue
            output = stage / filename
            with open(file, "rb") as inp, open(output, "xb") as out:
                shutil.copyfileobj(inp, out, length=1024 * 1024)
                out.flush()
                os.fsync(out.fileno())
        if not verify_backup_snapshot(source):
            raise ValueError("Snapshot changed while staging")
        return stage
    except Exception:
        shutil.rmtree(stage)
        raise
