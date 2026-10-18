"""StorageScope v4.57 - HLD/LLD governance module. Author: Abdelhalim Talbi."""
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


class Governance:
    def __init__(self, path):
        self.db = sqlite3.connect(str(path))
        try:
            self.db.execute('PRAGMA foreign_keys=ON')
            self.db.execute('PRAGMA busy_timeout=5000')
            self.db.executescript('''
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, rationale TEXT NOT NULL,
                author TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'PROPOSED',
                approver TEXT, approved_at TEXT, created_at TEXT NOT NULL,
                CHECK(status IN ('PROPOSED','APPROVED','REJECTED','DEFERRED')));
            CREATE TABLE IF NOT EXISTS reservations (
                id TEXT PRIMARY KEY, decision_id TEXT NOT NULL REFERENCES decisions(id),
                description TEXT NOT NULL, blocking INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'OPEN', owner TEXT NOT NULL,
                evidence TEXT, closed_by TEXT,
                CHECK(status IN ('OPEN','RESOLVED','ACCEPTED')));
            CREATE TABLE IF NOT EXISTS audit (
                seq INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
                actor TEXT NOT NULL, action TEXT NOT NULL, object_id TEXT NOT NULL,
                payload TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL);
            ''')
            self.db.execute('CREATE INDEX IF NOT EXISTS idx_reservations_decision_id ON reservations(decision_id,id)')
            self.db.commit()
        except BaseException:
            self.db.close()
            raise

    @contextmanager
    def _write_transaction(self):
        """Serialize the legacy audit read/append with the corresponding write."""
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.db.rollback()
            raise
        else:
            self.db.commit()

    def _audit(self, actor, action, obj, payload):
        previous = self.db.execute('SELECT hash FROM audit ORDER BY seq DESC LIMIT 1').fetchone()
        prev = previous[0] if previous else 'GENESIS'
        stamp = now()
        data = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(json.dumps([stamp, actor, action, obj, data, prev], ensure_ascii=False).encode()).hexdigest()
        self.db.execute('INSERT INTO audit(timestamp,actor,action,object_id,payload,prev_hash,hash) VALUES(?,?,?,?,?,?,?)', (stamp,actor,action,obj,data,prev,digest))

    def _require(self, **values):
        for name, value in values.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'{name} required')

    def propose(self, identifier, title, rationale, author):
        self._require(identifier=identifier, title=title, rationale=rationale, author=author)
        with self._write_transaction():
            self.db.execute('INSERT INTO decisions(id,title,rationale,author,created_at) VALUES(?,?,?,?,?)', (identifier,title,rationale,author,now()))
            self._audit(author,'PROPOSE',identifier,{'title':title,'rationale':rationale})

    def add_reservation(self, identifier, decision_id, description, owner, blocking=True):
        self._require(identifier=identifier, decision_id=decision_id, description=description, owner=owner)
        with self._write_transaction():
            self.db.execute('INSERT INTO reservations(id,decision_id,description,owner,blocking) VALUES(?,?,?,?,?)', (identifier,decision_id,description,owner,int(blocking)))
            self._audit(owner,'ADD_RESERVATION',identifier,{'decision_id':decision_id,'blocking':blocking,'description':description})

    def resolve_reservation(self, identifier, actor, evidence):
        self._require(identifier=identifier, actor=actor)
        if not evidence or not evidence.strip():
            raise ValueError('Evidence required')
        with self._write_transaction():
            cursor = self.db.execute("UPDATE reservations SET status='RESOLVED', evidence=?, closed_by=? WHERE id=? AND status='OPEN'",(evidence,actor,identifier))
            if cursor.rowcount != 1:
                raise ValueError('Reservation not open')
            self._audit(actor,'RESOLVE_RESERVATION',identifier,{'evidence':evidence})

    def decide(self, identifier, approver, status):
        self._require(identifier=identifier, approver=approver)
        if status not in ('APPROVED','REJECTED','DEFERRED'):
            raise ValueError('Invalid decision status')
        with self._write_transaction():
            if not self.verify_audit():
                raise ValueError('Audit integrity check failed')
            row = self.db.execute('SELECT author,status FROM decisions WHERE id=?',(identifier,)).fetchone()
            if not row or row[1] != 'PROPOSED':
                raise ValueError('Decision not proposed')
            if row[0] == approver:
                raise ValueError('Self-approval forbidden')
            if status == 'APPROVED':
                count = self.db.execute("SELECT COUNT(*) FROM reservations WHERE decision_id=? AND blocking=1 AND status='OPEN'",(identifier,)).fetchone()[0]
                if count:
                    raise ValueError('Blocking reservations remain open')
            self.db.execute('UPDATE decisions SET status=?,approver=?,approved_at=? WHERE id=?',(status,approver,now(),identifier))
            self._audit(approver,'DECISION_'+status,identifier,{'status':status})

    def verify_audit(self):
        prev = 'GENESIS'
        for stamp,actor,action,obj,payload,stored_prev,digest in self.db.execute('SELECT timestamp,actor,action,object_id,payload,prev_hash,hash FROM audit ORDER BY seq'):
            expected = hashlib.sha256(json.dumps([stamp,actor,action,obj,payload,prev],ensure_ascii=False).encode()).hexdigest()
            if stored_prev != prev or digest != expected:
                return False
            prev = digest
        return True

    def export_markdown(self):
        lines = ['# Registre HLD/LLD — StorageScope v4.57', 'Auteur : Abdelhalim Talbi', '', '| ID | Décision | État | Approbateur |', '|---|---|---|---|']
        for identifier,title,status,approver in self.db.execute('SELECT id,title,status,approver FROM decisions ORDER BY id'):
            safe = lambda s: str(s or '').replace('|','\\|').replace('\n',' ')
            lines.append(f'| {safe(identifier)} | {safe(title)} | {safe(status)} | {safe(approver)} |')
        lines.extend(['', '## Réserves', '| ID | Décision | État | Bloquante | Preuve |', '|---|---|---|---|---|'])
        for identifier,decision,status,blocking,evidence in self.db.execute('SELECT id,decision_id,status,blocking,evidence FROM reservations ORDER BY id'):
            safe = lambda s: str(s or '').replace('|','\\|').replace('\n',' ')
            lines.append(f'| {safe(identifier)} | {safe(decision)} | {safe(status)} | {bool(blocking)} | {safe(evidence)} |')
        content = '\n'.join(lines)+'\n'
        return content, hashlib.sha256(content.encode()).hexdigest()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False

    def close(self):
        """Rollback pending changes, close once and invalidate the handle."""
        db = self.db
        if db is None:
            return
        if getattr(self, "_closed", False):
            return
        self._closed = True
        try:
            if db.in_transaction:
                db.rollback()
        finally:
            db.close()
