"""Committee agenda, follow-ups and cross-meeting continuity. Author: Abdelhalim Talbi."""
import hashlib
import json
from datetime import date

class Planning:
    def __init__(self, committees):
        self.c = committees
        self.g = committees.g
        self.db = committees.db
        self.db.execute('''CREATE TABLE IF NOT EXISTS meeting_followups(
            id TEXT PRIMARY KEY, meeting_id TEXT NOT NULL REFERENCES meetings(id),
            decision_id TEXT NOT NULL REFERENCES decisions(id), owner TEXT NOT NULL,
            due_date TEXT NOT NULL, description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN','DONE')),
            evidence TEXT NOT NULL DEFAULT '')''')
    def add_followup(self, identifier, meeting_id, decision_id, owner, due_date, description, actor):
        self.c.guard()
        self.g._require(identifier=identifier, meeting_id=meeting_id, decision_id=decision_id, owner=owner, due_date=due_date, description=description, actor=actor)
        date.fromisoformat(due_date)
        with self.db:
            if not self.db.execute('SELECT 1 FROM meeting_decisions WHERE meeting_id=? AND decision_id=?',(meeting_id,decision_id)).fetchone():
                raise ValueError('Decision not linked to meeting')
            self.db.execute('INSERT INTO meeting_followups(id,meeting_id,decision_id,owner,due_date,description) VALUES(?,?,?,?,?,?)',(identifier,meeting_id,decision_id,owner,due_date,description))
            self.g._audit(actor,'FOLLOWUP_CREATED',identifier,{'meeting_id':meeting_id,'decision_id':decision_id,'due_date':due_date})
    def complete(self,identifier,actor,evidence):
        self.c.guard(); self.g._require(actor=actor,evidence=evidence)
        with self.db:
            cursor=self.db.execute("UPDATE meeting_followups SET status='DONE',evidence=? WHERE id=? AND status='OPEN'",(evidence,identifier))
            if cursor.rowcount!=1: raise ValueError('Unknown or completed follow-up')
            self.g._audit(actor,'FOLLOWUP_DONE',identifier,{'evidence_sha256':hashlib.sha256(evidence.encode()).hexdigest()})
    def agenda(self,meeting_id,as_of=None):
        self.c.guard()
        day=date.fromisoformat(as_of) if as_of else date.today()
        row=self.db.execute('SELECT title,scheduled_at,status FROM meetings WHERE id=?',(meeting_id,)).fetchone()
        if not row: raise ValueError('Unknown meeting')
        decisions=self.db.execute('''SELECT d.id,d.title,d.status FROM decisions d JOIN meeting_decisions md ON md.decision_id=d.id WHERE md.meeting_id=? ORDER BY d.id''',(meeting_id,)).fetchall()
        pending=self.db.execute('''SELECT f.id,f.decision_id,f.owner,f.due_date,f.description,f.status FROM meeting_followups f WHERE f.status='OPEN' AND (f.meeting_id=? OR f.decision_id IN (SELECT decision_id FROM meeting_decisions WHERE meeting_id=?)) ORDER BY f.due_date,f.id''',(meeting_id,meeting_id)).fetchall()
        reservations=self.db.execute('''SELECT r.id,r.decision_id,r.description,r.blocking FROM reservations r WHERE r.decision_id IN (SELECT decision_id FROM meeting_decisions WHERE meeting_id=?) AND r.status='OPEN' ORDER BY r.blocking DESC,r.id''',(meeting_id,)).fetchall()
        items=[]
        for rid,did,desc,blocking in reservations:
            items.append({'priority':0 if blocking else 2,'type':'RESERVE','id':rid,'decision_id':did,'description':desc})
        for fid,did,owner,due,desc,status in pending:
            items.append({'priority':1 if date.fromisoformat(due)<day else 3,'type':'FOLLOWUP','id':fid,'decision_id':did,'description':desc,'owner':owner,'due_date':due})
        for did,title,status in decisions:
            if status!='APPROVED':items.append({'priority':2,'type':'DECISION','id':did,'decision_id':did,'description':title,'status':status})
        items.sort(key=lambda x:(x['priority'],x['id']))
        return {'meeting_id':meeting_id,'title':row[0],'scheduled_at':row[1],'status':row[2],'as_of':day.isoformat(),'items':items}
    def agenda_markdown(self,meeting_id,as_of=None):
        data=self.agenda(meeting_id,as_of)
        safe=lambda s:str(s).replace('|','\\|').replace('\n',' ')
        lines=[f"# Ordre du jour — {safe(data['title'])}",f"Comité : {safe(meeting_id)} · Préparation : {data['as_of']}",'Auteur : Abdelhalim Talbi','','| Priorité | Type | Référence | Décision | Objet |','|---|---|---|---|---|']
        lines.extend(f"| P{x['priority']+1} | {x['type']} | {safe(x['id'])} | {safe(x['decision_id'])} | {safe(x['description'])} |" for x in data['items'])
        body='\n'.join(lines)+'\n'
        return body,hashlib.sha256(body.encode()).hexdigest()
