"""Human decision provenance, due-date queue and idempotent follow-ups. Author: Abdelhalim Talbi."""
import json
import sqlite3
from datetime import date
from architecture_decisions_v536 import DecisionStore, _required

class GovernanceStore(DecisionStore):
    def __init__(self, path):
        super().__init__(path)
        with self._connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS decision_links (
              decision_id TEXT NOT NULL, earlier_id TEXT NOT NULL, later_id TEXT NOT NULL,
              alert_code TEXT NOT NULL, evidence_id TEXT NOT NULL, earlier_sha256 TEXT NOT NULL,
              later_sha256 TEXT NOT NULL, PRIMARY KEY(decision_id,earlier_id,later_id,alert_code,evidence_id));
              CREATE TABLE IF NOT EXISTS decision_followups (
              decision_id TEXT NOT NULL, due_date TEXT NOT NULL, actor TEXT NOT NULL,
              note TEXT NOT NULL, PRIMARY KEY(decision_id,due_date));''')

    def link_event(self, decision_id, event, *, evidence_id='', actor='architect'):
        """Only links evidence explicitly present in a verified timeline event."""
        actor = _required(actor, 'actor')
        if not isinstance(event, dict): raise ValueError('invalid event')
        fields = ('earlier_id','later_id','code','earlier_sha256','later_sha256')
        values = [_required(event.get(k),k) for k in fields]
        evidence_id = evidence_id.strip() if isinstance(evidence_id,str) else None
        if evidence_id is None: raise ValueError('invalid evidence id')
        if evidence_id and evidence_id not in event.get('evidence_ids',[]):
            raise ValueError('evidence id not present in event')
        if not all(len(values[i])==64 and all(c in '0123456789abcdef' for c in values[i]) for i in (3,4)):
            raise ValueError('invalid campaign sha256')
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM decisions WHERE id=?',(decision_id,)).fetchone(): raise KeyError(decision_id)
            args = (decision_id,values[0],values[1],values[2],evidence_id,values[3],values[4])
            cur = db.execute('INSERT OR IGNORE INTO decision_links VALUES (?,?,?,?,?,?,?)',args)
            if cur.rowcount:
                self._append(db,decision_id,{'event':'EVIDENCE_LINKED','id':decision_id,'actor':actor,
                    'earlier_id':values[0],'later_id':values[1],'alert_code':values[2],
                    'evidence_id':evidence_id,'earlier_sha256':values[3],'later_sha256':values[4]})
            return bool(cur.rowcount)

    def followup(self, decision_id, actor, note, *, today=None):
        """Record a human follow-up once per due-date; no email or automatic notification."""
        actor=_required(actor,'actor');note=_required(note,'note')
        today=date.today() if today is None else date.fromisoformat(str(today))
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT due_date,status FROM decisions WHERE id=?',(decision_id,)).fetchone()
            if row is None: raise KeyError(decision_id)
            if row[1]=='CLOSED': raise ValueError('closed decision')
            if date.fromisoformat(row[0])>today: raise ValueError('not due')
            cur=db.execute('INSERT OR IGNORE INTO decision_followups VALUES (?,?,?,?)',
                           (decision_id,row[0],actor,note))
            if cur.rowcount:
                self._append(db,decision_id,{'event':'FOLLOWUP_RECORDED','id':decision_id,
                              'actor':actor,'note':note,'due_date':row[0]})
            return bool(cur.rowcount)

    def governance_report(self, *, today=None):
        today=date.today() if today is None else date.fromisoformat(str(today))
        # One consistent SQLite read transaction for all tables and the audit chain.
        with self._connect() as db:
            db.execute('BEGIN')
            report=self._report_from_db(db)
            links=[dict(zip(('decision_id','earlier_id','later_id','alert_code','evidence_id','earlier_sha256','later_sha256'),r))
                   for r in db.execute('SELECT * FROM decision_links ORDER BY decision_id,earlier_id,later_id,alert_code,evidence_id')]
            followups=[dict(zip(('decision_id','due_date','actor','note'),r))
                       for r in db.execute('SELECT * FROM decision_followups ORDER BY decision_id,due_date')]
        from collections import Counter
        link_counts=Counter(l['decision_id'] for l in links)
        followup_keys={(f['decision_id'],f['due_date']) for f in followups}
        decisions=[]
        for d in report['decisions']:
            item=dict(d)
            due=date.fromisoformat(d['due_date'])
            item['deadline_state']=('closed' if d['status']=='CLOSED' else
                                    'overdue' if due<today else 'due_today' if due==today else 'upcoming')
            item['linked_events']=link_counts[d['id']]
            item['followup_recorded']=(d['id'],d['due_date']) in followup_keys
            decisions.append(item)
        return {'schema':'storagescope.governance.v5.37','as_of':today.isoformat(),
                'decisions':decisions,'links':links,'followups':followups,
                'kpis':{'open':sum(d['status']!='CLOSED' for d in decisions),
                        'overdue':sum(d['deadline_state']=='overdue' for d in decisions),
                        'due_today':sum(d['deadline_state']=='due_today' for d in decisions),
                        'unlinked':sum(not d['linked_events'] for d in decisions),
                        'followups_recorded':len(followups)},
                'audit_head':report['audit_head'],'audit':report['audit'],'audit_verified':True,
                'recommendation_only':True,'production_activation':False,
                'author':'Abdelhalim Talbi'}

    def export_governance(self, destination, *, today=None):
        from campaign_report_v530 import _atomic_write
        data=self.governance_report(today=today)
        _atomic_write(destination,json.dumps(data,ensure_ascii=False,indent=2)+'\n')
        return data
