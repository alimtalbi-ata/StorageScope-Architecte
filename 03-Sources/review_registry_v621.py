"""Transactional, auditable review of reconciliation proposals; no inventory mutation."""
import argparse, datetime, hashlib, json, sqlite3
from contextlib import closing
from pathlib import Path

SCHEMA='''CREATE TABLE IF NOT EXISTS decisions (candidate_key TEXT PRIMARY KEY, status TEXT NOT NULL CHECK(status IN ('APPROVED','REJECTED')), reviewer TEXT NOT NULL, reason TEXT NOT NULL, decided_at TEXT NOT NULL, evidence_json TEXT NOT NULL); CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_key TEXT NOT NULL, event TEXT NOT NULL, reviewer TEXT NOT NULL, at TEXT NOT NULL, payload_json TEXT NOT NULL);'''

def candidate_key(candidate):
    evidence={'indices':candidate['indices'],'identity_evidence':candidate['identity_evidence'],'sources':candidate.get('sources',[])}
    return hashlib.sha256(json.dumps(evidence,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def decide(db, report, key, status, reviewer, reason):
    if status not in ('APPROVED','REJECTED') or not reviewer.strip() or not reason.strip():
        raise ValueError('Status, reviewer and reason required')
    candidates={candidate_key(c):c for c in report['reconciliation']['candidates']}
    if key not in candidates: raise ValueError('Candidate not found in supplied report')
    # sqlite3.Connection.__exit__ commits/rolls back but does NOT close on Windows.
    # Close deterministically after the transaction, including duplicate-decision errors.
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.executescript(SCHEMA)
        existing=conn.execute('SELECT status FROM decisions WHERE candidate_key=?',(key,)).fetchone()
        if existing: raise ValueError('Candidate already decided; immutable decision')
        now=datetime.datetime.now(datetime.timezone.utc).isoformat()
        payload=json.dumps(candidates[key],sort_keys=True,ensure_ascii=False)
        conn.execute('INSERT INTO decisions VALUES (?,?,?,?,?,?)',(key,status,reviewer,reason,now,payload))
        conn.execute('INSERT INTO events(candidate_key,event,reviewer,at,payload_json) VALUES (?,?,?,?,?)',(key,status,reviewer,now,payload))
    return {'candidate_key':key,'status':status,'inventory_changed':False}

def main():
    p=argparse.ArgumentParser(description='StorageScope review registry (no automatic merge)')
    p.add_argument('report',type=Path);p.add_argument('--db',type=Path,required=True)
    p.add_argument('--list',action='store_true');p.add_argument('--key');p.add_argument('--status',choices=['APPROVED','REJECTED']);p.add_argument('--reviewer');p.add_argument('--reason')
    a=p.parse_args(); report=json.loads(a.report.read_text(encoding='utf-8'))
    if a.list:
        print(json.dumps([{'key':candidate_key(c),'indices':c['indices'],'conflicts':len(c['conflicts'])} for c in report['reconciliation']['candidates']],indent=2));return
    if not all([a.key,a.status,a.reviewer,a.reason]):p.error('decision requires --key --status --reviewer --reason')
    print(json.dumps(decide(a.db,report,a.key,a.status,a.reviewer,a.reason),indent=2))
if __name__=='__main__':main()
