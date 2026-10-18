"""Transactional human architecture decisions, tamper-evident audit. Author: Abdelhalim Talbi."""
import hashlib
import json
import os
import sqlite3
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

STATUSES = {'OPEN', 'IN_REVIEW', 'APPROVED', 'REJECTED', 'CLOSED'}
TRANSITIONS = {'OPEN': {'IN_REVIEW'}, 'IN_REVIEW': {'APPROVED', 'REJECTED'},
               'APPROVED': {'CLOSED'}, 'REJECTED': {'CLOSED'}, 'CLOSED': set()}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def _required(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise ValueError('invalid ' + label)
    return value.strip()


class ClosingConnection(sqlite3.Connection):
    """Commit/rollback as usual, then close the connection on context exit."""
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class DecisionStore:
    """Tracks human decisions only; never changes any routing policy."""
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS decisions (
              id TEXT PRIMARY KEY, subject TEXT NOT NULL, owner TEXT NOT NULL,
              due_date TEXT NOT NULL, evidence TEXT NOT NULL, status TEXT NOT NULL,
              rationale TEXT NOT NULL DEFAULT '', approval TEXT NOT NULL DEFAULT '');
              CREATE TABLE IF NOT EXISTS decision_audit (
              seq INTEGER PRIMARY KEY AUTOINCREMENT, decision_id TEXT NOT NULL,
              payload TEXT NOT NULL, previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL);''')

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10, factory=ClosingConnection)
        try:
            db.execute('PRAGMA busy_timeout=10000')
            return db
        except BaseException:
            db.close()
            raise

    @staticmethod
    def _append(db, ident, payload):
        row = db.execute('SELECT entry_hash FROM decision_audit ORDER BY seq DESC LIMIT 1').fetchone()
        prev = row[0] if row else '0' * 64
        raw = canonical(payload)
        digest = hashlib.sha256((prev + raw).encode('utf-8')).hexdigest()
        db.execute('INSERT INTO decision_audit(decision_id,payload,previous_hash,entry_hash) VALUES (?,?,?,?)',
                   (ident, raw, prev, digest))

    def create(self, ident, subject, owner, due_date, evidence):
        ident = _required(ident, 'id'); subject = _required(subject, 'subject')
        owner = _required(owner, 'owner'); evidence = _required(evidence, 'evidence')
        date.fromisoformat(_required(due_date, 'due_date'))
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM decisions WHERE id=?', (ident,)).fetchone():
                raise ValueError('decision already exists')
            db.execute('INSERT INTO decisions(id,subject,owner,due_date,evidence,status) VALUES (?,?,?,?,?,?)',
                       (ident, subject, owner, due_date, evidence, 'OPEN'))
            self._append(db, ident, {'event':'CREATED','id':ident,'subject':subject,'owner':owner,
                                      'due_date':due_date,'evidence':evidence,'status':'OPEN'})
        return self.get(ident)

    def get(self, ident):
        with self._connect() as db:
            row = db.execute('SELECT id,subject,owner,due_date,evidence,status,rationale,approval FROM decisions WHERE id=?',
                             (ident,)).fetchone()
        if row is None: raise KeyError(ident)
        return dict(zip(('id','subject','owner','due_date','evidence','status','rationale','approval'),row))

    def transition(self, ident, status, actor, rationale, *, approval=None):
        actor = _required(actor, 'actor'); rationale = _required(rationale, 'rationale')
        if status not in STATUSES: raise ValueError('invalid status')
        if status == 'APPROVED': approval = _required(approval, 'approval')
        elif approval is not None: raise ValueError('approval only valid for APPROVED')
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT status FROM decisions WHERE id=?', (ident,)).fetchone()
            if row is None: raise KeyError(ident)
            if status not in TRANSITIONS[row[0]]: raise ValueError('invalid status transition')
            db.execute('UPDATE decisions SET status=?,rationale=?,approval=? WHERE id=?',
                       (status,rationale,approval or '',ident))
            self._append(db,ident,{'event':'TRANSITION','id':ident,'from':row[0], 'to':status,
                                   'actor':actor,'rationale':rationale,'approval':approval})
        return self.get(ident)

    @staticmethod
    def _report_from_db(db):
        """Read decisions and audit in one SQLite snapshot; verify before returning."""
        decisions = [dict(zip(('id','subject','owner','due_date','evidence','status','rationale','approval'), r))
                     for r in db.execute('SELECT id,subject,owner,due_date,evidence,status,rationale,approval FROM decisions ORDER BY id')]
        rows = db.execute('SELECT seq,decision_id,payload,previous_hash,entry_hash FROM decision_audit ORDER BY seq').fetchall()
        prev = '0' * 64
        audit = []
        for seq, ident, raw, previous, digest in rows:
            if previous != prev or hashlib.sha256((prev + raw).encode('utf-8')).hexdigest() != digest:
                raise ValueError('audit integrity failure')
            event = json.loads(raw)
            if not isinstance(event, dict):
                raise ValueError('invalid audit payload')
            audit.append({'seq':seq,'decision_id':ident,'event':event,'previous_hash':previous,'entry_hash':digest})
            prev = digest
        return {'schema':'storagescope.decision-tracking.v5.36','author':'Abdelhalim Talbi',
                'decisions':decisions,'audit':audit,'audit_head':prev,'audit_verified':True,
                'recommendation_only':True,'production_activation':False}

    def report(self):
        with self._connect() as db:
            db.execute('BEGIN')
            return self._report_from_db(db)

    def export(self, destination):
        destination = Path(destination)
        report = self.report()
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix='.decision-',suffix='.json',dir=destination.parent)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as handle:
                handle.write(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
                handle.flush(); os.fsync(handle.fileno())
            os.replace(temp,destination)
        finally:
            if os.path.exists(temp): os.unlink(temp)
        return report
