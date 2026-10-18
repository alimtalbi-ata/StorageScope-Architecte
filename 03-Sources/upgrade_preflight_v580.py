"""Read-only upgrade preflight for StorageScope user data. Author: Abdelhalim Talbi."""
from pathlib import Path
import sqlite3
from contextlib import closing

DB_NAMES = ('architecture-decisions.sqlite', 'campaigns.sqlite')

def inspect_data_directory(directory):
    """Return diagnostic findings without creating, modifying, or repairing files."""
    root = Path(directory)
    findings = []
    if not root.exists():
        return {'safe': True, 'databases': [], 'findings': ['DATA_DIRECTORY_ABSENT']}
    if not root.is_dir() or root.is_symlink():
        return {'safe': False, 'databases': [], 'findings': ['UNSAFE_DATA_DIRECTORY']}
    databases = []
    for name in DB_NAMES:
        path = root / name
        if not path.exists() and not path.is_symlink():
            continue
        if path.is_symlink() or not path.is_file():
            findings.append('UNSAFE_DATABASE:' + name)
            continue
        try:
            with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=2)) as con:
                check = con.execute('PRAGMA quick_check').fetchone()[0]
                schema = con.execute('PRAGMA user_version').fetchone()[0]
            if check != 'ok':
                findings.append('CORRUPT_DATABASE:' + name)
            databases.append({'name': name, 'schema_version': schema, 'integrity': check})
        except (sqlite3.Error, OSError) as exc:
            findings.append('UNREADABLE_DATABASE:' + name + ':' + type(exc).__name__)
    return {'safe': not any(x.startswith(('UNSAFE_', 'CORRUPT_', 'UNREADABLE_')) for x in findings),
            'databases': databases, 'findings': findings}
