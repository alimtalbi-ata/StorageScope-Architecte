"""Read-only operational dashboard. Never initializes a missing database.
Author: Abdelhalim Talbi.
"""
from pathlib import Path
import sqlite3
from contextlib import closing
from datetime import date


def _read_existing(path, query):
    path = Path(path)
    if not path.is_file():
        return None
    # URI read-only avoids accidentally creating or modifying a user's database.
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2)) as db:
        return db.execute(query).fetchall()


def dashboard_summary(paths, *, today=None):
    """Return counts and human-readable errors without mutating either DB."""
    today = date.today() if today is None else date.fromisoformat(str(today))
    result = {'decisions': None, 'overdue': None, 'due_today': None,
              'campaigns': None, 'errors': {}, 'empty': {}}
    try:
        rows = _read_existing(paths['decisions'],
            'SELECT status, due_date FROM decisions')
        if rows is None:
            result['empty']['decisions'] = True
        else:
            result['decisions'] = sum(status != 'CLOSED' for status, due in rows)
            result['overdue'] = sum(status != 'CLOSED' and due < today.isoformat() for status, due in rows)
            result['due_today'] = sum(status != 'CLOSED' and due == today.isoformat() for status, due in rows)
    except (sqlite3.Error, OSError, ValueError) as exc:
        result['errors']['decisions'] = str(exc)
    try:
        rows = _read_existing(paths['campaigns'], 'SELECT COUNT(*) FROM campaigns')
        if rows is None:
            result['empty']['campaigns'] = True
        else:
            result['campaigns'] = rows[0][0]
    except (sqlite3.Error, OSError, ValueError) as exc:
        result['errors']['campaigns'] = str(exc)
    return result


def metric_label(value, missing=False, error=False):
    if error: return 'Erreur · diagnostic requis'
    if missing: return 'À initialiser'
    return str(value) if value is not None else 'Indisponible'
