"""Traceability extension for StorageScope governance. Author: Abdelhalim Talbi."""
import json
from governance import Governance

class Traceability:
    TYPES = {'ADR','ACTION','EVIDENCE','DOCUMENT'}
    def __init__(self, governance: Governance):
        self.g = governance
        self.db = governance.db
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS artifacts (
          id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('ADR','ACTION','EVIDENCE','DOCUMENT')),
          title TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('OPEN','DONE')),
          owner TEXT NOT NULL, reference TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS artifact_links (
          decision_id TEXT NOT NULL REFERENCES decisions(id),
          artifact_id TEXT NOT NULL REFERENCES artifacts(id),
          PRIMARY KEY(decision_id, artifact_id));
        ''')
        self.db.execute('CREATE INDEX IF NOT EXISTS idx_artifact_links_artifact_id ON artifact_links(artifact_id)')
    def _guard(self):
        if not self.g.verify_audit():
            raise ValueError('Audit integrity check failed')
    def add(self, identifier, kind, title, owner, reference='', actor=None):
        self._guard()
        self.g._require(identifier=identifier, title=title, owner=owner)
        if kind not in self.TYPES: raise ValueError('Invalid artifact type')
        with self.db:
            self.db.execute('INSERT INTO artifacts VALUES(?,?,?,?,?,?)',(identifier,kind,title,'OPEN',owner,reference))
            self.g._audit(actor or owner,'ARTIFACT_CREATED',identifier,{'kind':kind,'title':title,'reference':reference})
    def link(self, decision_id, artifact_id, actor):
        self._guard(); self.g._require(actor=actor)
        with self.db:
            self.db.execute('INSERT INTO artifact_links VALUES(?,?)',(decision_id,artifact_id))
            self.g._audit(actor,'ARTIFACT_LINKED',decision_id,{'artifact_id':artifact_id})
    def complete(self, artifact_id, actor, evidence):
        self._guard(); self.g._require(actor=actor,evidence=evidence)
        with self.db:
            cur=self.db.execute("UPDATE artifacts SET state='DONE',reference=? WHERE id=? AND state='OPEN'",(evidence,artifact_id))
            if cur.rowcount!=1: raise ValueError('Artifact not open')
            self.g._audit(actor,'ARTIFACT_COMPLETED',artifact_id,{'evidence':evidence})
    def closure_readiness(self, decision_id):
        self._guard()
        row=self.db.execute('SELECT status FROM decisions WHERE id=?',(decision_id,)).fetchone()
        if row is None: raise ValueError('Unknown decision')
        issues=[]
        if row[0]!='APPROVED': issues.append('Decision not approved')
        for rid, in self.db.execute("SELECT id FROM reservations WHERE decision_id=? AND blocking=1 AND status='OPEN'",(decision_id,)):
            issues.append('Blocking reservation: '+rid)
        artifacts=self.db.execute('''SELECT a.id,a.kind,a.state,a.reference FROM artifacts a
           JOIN artifact_links l ON l.artifact_id=a.id WHERE l.decision_id=? ORDER BY a.id''',(decision_id,)).fetchall()
        for aid,kind,state,reference in artifacts:
            if kind=='ACTION' and state!='DONE': issues.append('Action unfinished: '+aid)
            if kind=='EVIDENCE' and (state!='DONE' or not reference.strip()): issues.append('Evidence missing: '+aid)
        if not any(a[1]=='EVIDENCE' and a[2]=='DONE' and a[3].strip() for a in artifacts):
            issues.append('No completed evidence linked')
        return {'decision_id':decision_id,'ready':not issues,'issues':issues,
                'artifacts':[{'id':a,'kind':k,'state':s,'reference':r} for a,k,s,r in artifacts]}
    def export_json(self, decision_id):
        return json.dumps(self.closure_readiness(decision_id),ensure_ascii=False,indent=2)
