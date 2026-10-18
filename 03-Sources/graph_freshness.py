"""Conservative file fingerprint for SQLite and its WAL sidecar. Author: Abdelhalim Talbi."""
from pathlib import Path

def database_fingerprint(path):
    """Detect external file writes without opening or sharing SQLite connections."""
    base = Path(path)
    result = []
    for suffix in ('', '-wal', '-shm'):
        target = Path(str(base) + suffix)
        try:
            stat = target.stat()
            result.append((suffix, stat.st_mtime_ns, stat.st_size, stat.st_ino))
        except FileNotFoundError:
            result.append((suffix, None, None, None))
    return tuple(result)
