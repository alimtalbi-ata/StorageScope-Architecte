"""Committee meeting registry for StorageScope. Author: Abdelhalim Talbi."""
import hashlib
import json
from governance import now

class Committees:
    def __init__(self, governance):
        self.g=governance; self.db=governance.db
        self.db.executescript('''CREATE TABLE IF NOT EXISTS meetings(id TEXT PRIMARY KEY,title TEXT NOT NULL,scheduled_at TEXT NOT NULL,chair TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'DRAFT' CHECK(status IN ('DRAFT','HELD','CLOSED')),minutes TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS meeting_attendees(meeting_id TEXT NOT NULL REFERENCES meetings(id),participant TEXT NOT NULL,role TEXT NOT NULL,PRIMARY KEY(meeting_id,participant));
        CREATE TABLE IF NOT EXISTS meeting_decisions(meeting_id TEXT NOT NULL REFERENCES meetings(id),decision_id TEXT NOT NULL REFERENCES decisions(id),PRIMARY KEY(meeting_id,decision_id));''')
    def guard(self):
        if not self.g.verify_audit(): raise ValueError('Audit integrity check failed')
    def create(self,identifier,title,scheduled_at,chair):
        self.guard();self.g._require(identifier=identifier,title=title,scheduled_at=scheduled_at,chair=chair)
        with self.db:
            self.db.execute('INSERT INTO meetings(id,title,scheduled_at,chair) VALUES(?,?,?,?)',(identifier,title,scheduled_at,chair))
            self.g._audit(chair,'MEETING_CREATED',identifier,{'title':title,'scheduled_at':scheduled_at})
    def attendee(self,meeting_id,participant,role,actor):
        self.guard();self.g._require(meeting_id=meeting_id,participant=participant,role=role,actor=actor)
        with self.db:
            self._draft(meeting_id)
            self.db.execute('INSERT INTO meeting_attendees VALUES(?,?,?)',(meeting_id,participant,role))
            self.g._audit(actor,'MEETING_ATTENDEE',meeting_id,{'participant':participant,'role':role})
    def link(self,meeting_id,decision_id,actor):
        self.guard();self.g._require(actor=actor)
        with self.db:
            self._draft(meeting_id)
            self.db.execute('INSERT INTO meeting_decisions VALUES(?,?)',(meeting_id,decision_id))
            self.g._audit(actor,'MEETING_DECISION_LINK',meeting_id,{'decision_id':decision_id})
    def _draft(self,meeting_id):
        row=self.db.execute('SELECT status FROM meetings WHERE id=?',(meeting_id,)).fetchone()
        if not row or row[0]!='DRAFT': raise ValueError('Meeting is not editable')
    def hold(self,meeting_id,actor,minutes):
        self.guard();self.g._require(actor=actor,minutes=minutes)
        with self.db:
            self._draft(meeting_id)
            if not self.db.execute('SELECT 1 FROM meeting_attendees WHERE meeting_id=?',(meeting_id,)).fetchone(): raise ValueError('No attendees')
            self.db.execute("UPDATE meetings SET status='HELD',minutes=? WHERE id=?",(minutes,meeting_id))
            self.g._audit(actor,'MEETING_HELD',meeting_id,{'minutes_sha256':hashlib.sha256(minutes.encode()).hexdigest()})
    def close(self,meeting_id,actor,traceability):
        self.guard();self.g._require(actor=actor)
        with self.db:
            row=self.db.execute('SELECT status FROM meetings WHERE id=?',(meeting_id,)).fetchone()
            if not row or row[0]!='HELD': raise ValueError('Meeting not held')
            decisions=[r[0] for r in self.db.execute('SELECT decision_id FROM meeting_decisions WHERE meeting_id=?',(meeting_id,))]
            if not decisions: raise ValueError('No decisions linked')
            for did in decisions:
                report=traceability.closure_readiness(did)
                if not report['ready']: raise ValueError('Closure blocked for '+did+': '+', '.join(report['issues']))
            self.db.execute("UPDATE meetings SET status='CLOSED' WHERE id=?",(meeting_id,))
            self.g._audit(actor,'MEETING_CLOSED',meeting_id,{'decisions':decisions})
    def report(self,meeting_id):
        self.guard()
        row=self.db.execute('SELECT id,title,scheduled_at,chair,status,minutes FROM meetings WHERE id=?',(meeting_id,)).fetchone()
        if not row: raise ValueError('Unknown meeting')
        attendees=self.db.execute('SELECT participant,role FROM meeting_attendees WHERE meeting_id=? ORDER BY participant',(meeting_id,)).fetchall()
        decisions=self.db.execute('SELECT d.id,d.title,d.status FROM decisions d JOIN meeting_decisions l ON l.decision_id=d.id WHERE l.meeting_id=? ORDER BY d.id',(meeting_id,)).fetchall()
        def safe(x):return str(x).replace('|','\\|').replace('\n',' ')
        lines=[f'# Comité {safe(row[0])} — {safe(row[1])}',f'Date : {safe(row[2])} · Président : {safe(row[3])} · État : {row[4]}','Auteur logiciel : Abdelhalim Talbi','','## Participants','| Nom | Rôle |','|---|---|']
        lines += [f'| {safe(p)} | {safe(r)} |' for p,r in attendees]
        lines += ['','## Décisions','| ID | Objet | État |','|---|---|---|']
        lines += [f'| {safe(i)} | {safe(t)} | {s} |' for i,t,s in decisions]
        lines += ['','## Compte rendu',row[5] or '(non renseigné)']
        content='\n'.join(lines)+'\n'
        return content,hashlib.sha256(content.encode()).hexdigest()
