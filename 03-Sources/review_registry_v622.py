"""StorageScope v6.22: stable identity review, atomic SQLite audit chain, no mutation."""
import argparse
import datetime as dt
import hashlib
import json
import sqlite3
from pathlib import Path

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))

def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()

def candidate_key(candidate):
    """Use durable asset identifiers; reject ambiguous index-only candidates."""
    ids = candidate.get('asset_ids')
    if not isinstance(ids, list) or len(ids) < 2 or any(not isinstance(x, str) or not x.strip() for x in ids):
        raise ValueError('At least two stable asset_ids are required; indices are not identities')
    normalized = sorted(set(x.strip().casefold() for x in ids))
    if len(normalized) < 2:
        raise ValueError('Candidate must contain two distinct stable asset identifiers')
    return digest({'asset_ids': normalized, 'identity_evidence': sorted(set(map(str, candidate.get('identity_evidence', []))))})

SCHEMA = '''CREATE TABLE IF NOT EXISTS decisions (candidate_key TEXT PRIMARY KEY, status TEXT NOT NULL CHECK(status IN ('APPROVED','REJECTED')), reviewer TEXT NOT NULL, reason TEXT NOT NULL, decided_at TEXT NOT NULL, evidence_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY AUTOINCREMENT, candidate_key TEXT NOT NULL, action TEXT NOT NULL, reviewer TEXT NOT NULL, at TEXT NOT NULL, payload_json TEXT NOT NULL, previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL UNIQUE);'''

def decide(db, report, key, status, reviewer, reason):
    if status not in ('APPROVED', 'REJECTED') or not isinstance(reviewer, str) or not reviewer.strip() or not isinstance(reason, str) or not reason.strip():
        raise ValueError('Valid status, reviewer and reason required')
    # Recheck authorization at the persistence boundary: callers may bypass the UI.
    candidates = {}
    for candidate in report['reconciliation']['candidates']:
        if not isinstance(candidate, dict):
            continue
        if candidate.get('review_eligibility') not in (None, 'ELIGIBLE', 'REVIEW_REQUIRED'):
            continue
        if (candidate.get('action') == 'BLOCKED' or candidate.get('contradictions')
                or candidate.get('identity_conflicts') or candidate.get('identity_disagreements')
                or candidate.get('blocking_reasons') or candidate.get('risk') == 'HIGH'):
            continue
        try:
            candidate_id = candidate_key(candidate)
        except (ValueError, TypeError, KeyError):
            continue
        if candidate.get('review_key') not in (None, candidate_id):
            continue
        if candidate_id in candidates:
            raise ValueError('Ambiguous candidate identity in report')
        candidates[candidate_id] = candidate
    if key not in candidates:
        raise ValueError('Candidate not eligible for a review decision')
    db = Path(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db, timeout=15, isolation_level=None) as conn:
        conn.execute('PRAGMA busy_timeout=15000')
        conn.execute('BEGIN IMMEDIATE')
        try:
            for statement in SCHEMA.strip().split(';'):
                if statement.strip(): conn.execute(statement)
            if conn.execute('SELECT 1 FROM decisions WHERE candidate_key=?', (key,)).fetchone():
                raise ValueError('Immutable decision already exists')
            now = dt.datetime.now(dt.timezone.utc).isoformat()
            evidence = canonical(candidates[key])
            conn.execute('INSERT INTO decisions VALUES (?,?,?,?,?,?)', (key, status, reviewer.strip(), reason.strip(), now, evidence))
            row = conn.execute('SELECT event_hash FROM audit ORDER BY seq DESC LIMIT 1').fetchone()
            prev = row[0] if row else '0'*64
            payload = canonical({'status': status, 'reason': reason.strip(), 'evidence': candidates[key]})
            event = {'candidate_key': key, 'action': status, 'reviewer': reviewer.strip(), 'at': now, 'payload_json': payload, 'previous_hash': prev}
            h = digest(event)
            conn.execute('INSERT INTO audit(candidate_key,action,reviewer,at,payload_json,previous_hash,event_hash) VALUES (?,?,?,?,?,?,?)', (key,status,reviewer.strip(),now,payload,prev,h))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {'candidate_key': key, 'status': status, 'inventory_changed': False, 'audit_hash': h}

def verify(db):
    with sqlite3.connect(db) as conn:
        rows = conn.execute('SELECT candidate_key,action,reviewer,at,payload_json,previous_hash,event_hash FROM audit ORDER BY seq').fetchall()
        prev = '0'*64
        for i, row in enumerate(rows, 1):
            event = dict(zip(('candidate_key','action','reviewer','at','payload_json','previous_hash'), row[:6]))
            if event['previous_hash'] != prev or digest(event) != row[6]:
                return {'valid': False, 'failed_event': i, 'events_checked': i-1}
            prev = row[6]
        decisions = conn.execute('SELECT COUNT(*) FROM decisions').fetchone()[0]
    return {'valid': decisions == len(rows), 'events_checked': len(rows), 'decisions': decisions, 'warning': 'Hash chain is not externally anchored; full database replacement cannot be detected'}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--db',required=True)
    p.add_argument('--verify',action='store_true')
    p.add_argument('--report')
    p.add_argument('--list',action='store_true')
    p.add_argument('--key'); p.add_argument('--status',choices=['APPROVED','REJECTED']); p.add_argument('--reviewer'); p.add_argument('--reason')
    a=p.parse_args()
    if a.verify:
        result=verify(a.db); print(json.dumps(result,indent=2)); raise SystemExit(0 if result['valid'] else 1)
    if not a.report: p.error('--report required')
    report=json.loads(Path(a.report).read_text(encoding='utf-8'))
    if a.list:
        print(json.dumps([{'key':candidate_key(c),'asset_ids':c['asset_ids']} for c in report['reconciliation']['candidates']],indent=2));return
    if not all((a.key,a.status,a.reviewer,a.reason)): p.error('decision requires --key --status --reviewer --reason')
    print(json.dumps(decide(a.db,report,a.key,a.status,a.reviewer,a.reason),indent=2))
if __name__=='__main__': main()
