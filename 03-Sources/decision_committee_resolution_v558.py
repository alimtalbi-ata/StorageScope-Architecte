"""Audited, explicit human committee resolutions. Author: Abdelhalim Talbi."""
import json
from datetime import date
from architecture_decisions_v536 import _required
from decision_governance_v537 import GovernanceStore
from decision_integrity_v540 import consistency_report
from campaign_report_v530 import _atomic_write

VERDICTS = ('APPROVE', 'REJECT', 'DEFER')

class CommitteeResolutionStore(GovernanceStore):
    def __init__(self, path):
        super().__init__(path)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS committee_resolutions (
                audit_seq INTEGER PRIMARY KEY, decision_id TEXT NOT NULL,
                actor TEXT NOT NULL, meeting_date TEXT NOT NULL,
                verdict TEXT NOT NULL, rationale TEXT NOT NULL)""")

    def resolve(self, decision_id, actor, meeting_date, verdict, rationale):
        decision_id = _required(decision_id, 'decision_id')
        actor = _required(actor, 'actor')
        rationale = _required(rationale, 'rationale')
        meeting_date = date.fromisoformat(_required(meeting_date, 'meeting_date')).isoformat()
        if verdict not in VERDICTS:
            raise ValueError('invalid committee verdict')
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM decisions WHERE id=?',(decision_id,)).fetchone():
                raise KeyError(decision_id)
            # Write lock prevents intervening writers; verify audit chain inside lock.
            self._report_from_db(db)
            payload={'event':'COMMITTEE_RESOLVED','id':decision_id,'actor':actor,
                     'meeting_date':meeting_date,'verdict':verdict,'rationale':rationale}
            self._append(db,decision_id,payload)
            seq=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            db.execute('INSERT INTO committee_resolutions VALUES (?,?,?,?,?,?)',
                       (seq,decision_id,actor,meeting_date,verdict,rationale))
        return {'audit_seq':seq,'decision_id':decision_id,'human_recorded':True,'production_activation':False}

    def resolutions(self, decision_id=None):
        with self._connect() as db:
            db.execute('BEGIN')
            base=self._report_from_db(db)
            rows=db.execute('SELECT audit_seq,decision_id,actor,meeting_date,verdict,rationale FROM committee_resolutions ORDER BY audit_seq').fetchall()
        events={e['seq']:e for e in base['audit']}
        expected={e['seq'] for e in base['audit'] if e['event'].get('event')=='COMMITTEE_RESOLVED'}
        if expected!={r[0] for r in rows}:raise ValueError('committee ledger mismatch')
        out=[]
        for seq,ident,actor,meeting,verdict,rationale in rows:
            payload={'event':'COMMITTEE_RESOLVED','id':ident,'actor':actor,
                     'meeting_date':meeting,'verdict':verdict,'rationale':rationale}
            if (seq not in events or events[seq]['decision_id']!=ident or events[seq]['event']!=payload
                or verdict not in VERDICTS or not actor.strip() or not rationale.strip()):
                raise ValueError('committee audit mismatch')
            try:date.fromisoformat(meeting)
            except ValueError as exc:raise ValueError('invalid meeting date') from exc
            out.append({'audit_seq':seq,'decision_id':ident,'actor':actor,'meeting_date':meeting,
                        'verdict':verdict,'rationale':rationale,'production_activation':False})
        return [r for r in out if decision_id is None or r['decision_id']==decision_id]

def export_resolutions(store, destination, decision_id=None):
    entries=store.resolutions(decision_id)
    checked=consistency_report(store)
    if not checked['consistent']:raise ValueError('decision consistency failure')
    result={'schema':'storagescope.committee-resolutions.v5.58','audit_head':checked['audit_head'],
            'resolutions':entries,'production_activation':False,'author':'Abdelhalim Talbi'}
    _atomic_write(destination,json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result
