"""Read-only SQLite upgrade readiness checks; never mutates user databases."""
import sqlite3
from contextlib import closing
from pathlib import Path

class UpgradeBlocked(RuntimeError):
    pass

def inspect_database(path):
    path = Path(path)
    if not path.is_file():
        return {"path": str(path), "status": "absent"}
    if path.stat().st_size == 0:
        raise UpgradeBlocked(f"Empty database: {path}")
    # SQLite URI mode=ro prevents accidental database creation and changes.
    import urllib.parse
    uri = 'file:' + urllib.parse.quote(str(path.resolve()), safe='/') + '?mode=ro'
    try:
        with closing(sqlite3.connect(uri, uri=True, timeout=2)) as db:
            integrity = db.execute('PRAGMA quick_check').fetchone()[0]
            user_version = db.execute('PRAGMA user_version').fetchone()[0]
            schema_version = db.execute('PRAGMA schema_version').fetchone()[0]
            if integrity != 'ok':
                raise UpgradeBlocked(f"Integrity failure: {path}: {integrity}")
            return {"path": str(path), "status": "ok", "user_version": user_version, "schema_version": schema_version}
    except sqlite3.DatabaseError as exc:
        raise UpgradeBlocked(f"Unreadable SQLite database: {path}: {exc}") from exc

def preflight(paths):
    results = [inspect_database(path) for path in paths]
    if not any(item['status'] == 'ok' for item in results):
        raise UpgradeBlocked('No existing database to protect')
    return results
