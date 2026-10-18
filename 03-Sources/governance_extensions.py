"""Governance read model and conservative release gate. Author: Abdelhalim Talbi."""
from collections import Counter
import hashlib
import json
from pathlib import Path


def overview(governance):
    db = governance.db
    decisions = dict(db.execute('SELECT status,COUNT(*) FROM decisions GROUP BY status'))
    reservations = dict(db.execute('SELECT status,COUNT(*) FROM reservations GROUP BY status'))
    blocking = db.execute("SELECT COUNT(*) FROM reservations WHERE blocking=1 AND status='OPEN'").fetchone()[0]
    return {'decisions': decisions, 'reservations': reservations, 'blocking_open': blocking,
            'audit_valid': governance.verify_audit(),
            'pending_approvals': decisions.get('PROPOSED', 0)}


def decision_readiness(governance, identifier):
    row = governance.db.execute('SELECT id,title,status,author FROM decisions WHERE id=?', (identifier,)).fetchone()
    if row is None:
        raise ValueError('Unknown decision')
    reservations = governance.db.execute('SELECT id,description FROM reservations WHERE decision_id=? AND blocking=1 AND status=\'OPEN\' ORDER BY id', (identifier,)).fetchall()
    issues = []
    if row[2] != 'PROPOSED':
        issues.append('Decision is not proposed')
    if not governance.verify_audit():
        issues.append('Audit integrity check failed')
    issues.extend(f'Blocking reservation {r[0]}: {r[1]}' for r in reservations)
    return {'id': identifier, 'ready_for_review': not issues, 'issues': issues}


def export_snapshot(governance, destination):
    """Generate verifiable report + JSON summary, refusing broken audit chains."""
    if not governance.verify_audit():
        raise ValueError('Audit integrity check failed; export refused')
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    report, digest = governance.export_markdown()
    # Atomic replace of each output; not an atomic transaction across all files.
    import os, tempfile
    def atomic_write(path, data):
        fd, name = tempfile.mkstemp(prefix='.storagescope-', dir=str(path.parent))
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(name, path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
    atomic_write(destination, report.encode('utf-8'))
    atomic_write(Path(str(destination)+'.sha256'), (digest+'  '+destination.name+'\n').encode('ascii'))
    summary = overview(governance)
    summary['report_sha256'] = digest
    atomic_write(Path(str(destination)+'.json'), (json.dumps(summary, indent=2, ensure_ascii=False)+'\n').encode('utf-8'))
    return summary
