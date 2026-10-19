"""Conservative snapshot restore preparation. Author: Abdelhalim Talbi.

This module deliberately never overwrites active application files.
"""
from __future__ import annotations
import os
import hashlib
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
            if file.is_symlink() or not file.is_file():
                raise ValueError(f"Unsafe snapshot member: {filename}")
            source_digest = hashlib.sha256()
            with open(file, "rb") as inp, open(output, "xb") as out:
                while chunk := inp.read(1024 * 1024):
                    source_digest.update(chunk)
                    out.write(chunk)
                out.flush()
                os.fsync(out.fileno())
            with open(output, "rb") as staged:
                staged_digest = hashlib.file_digest(staged, "sha256")
            if staged_digest.digest() != source_digest.digest():
                raise ValueError(f"Staged copy integrity mismatch: {filename}")
        if not verify_backup_snapshot(source):
            raise ValueError("Snapshot changed while staging")
        for filename in ALLOWED:
            staged = stage / filename
            original = source / filename
            if staged.exists() != original.exists():
                raise ValueError(f"Snapshot member changed during staging: {filename}")
            if staged.exists():
                with staged.open("rb") as copied, original.open("rb") as reference:
                    if hashlib.file_digest(copied, "sha256").digest() != hashlib.file_digest(reference, "sha256").digest():
                        raise ValueError(f"Snapshot member changed during staging: {filename}")
        return stage
    except Exception:
        shutil.rmtree(stage)
        raise
