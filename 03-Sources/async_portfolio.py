"""Thread-safe read-only portfolio loader. Author: Abdelhalim Talbi."""
import sqlite3
from pathlib import Path
from governance import Governance
from portfolio import portfolio_snapshot
from cursor_pagination import decision_page

CacheKey = tuple

def load_portfolio_readonly(path, mode='filtered', **params):
    """Open one independent read-only SQLite connection; never touch Tk from workers."""
    if mode not in ('filtered','cursor'):
        raise ValueError('Mode de lecture invalide')
    resolved=Path(path).resolve()
    db=sqlite3.connect(resolved.as_uri()+'?mode=ro',uri=True,timeout=5)
    try:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')  # consistent snapshot across multiple SELECT statements
        g=Governance.__new__(Governance)
        g.db=db
        if mode=='cursor':
            result=decision_page(g,**params)
        else:
            result=portfolio_snapshot(g,None,**params)
        db.execute('COMMIT')
        return result
    except BaseException:
        if db.in_transaction:
            try:
                db.rollback()
            except sqlite3.Error:
                pass  # Preserve the original query/commit exception.
        raise
    finally:
        try:
            db.close()
        except sqlite3.Error:
            # SQLite close failures are not actionable after a completed read.
            pass
