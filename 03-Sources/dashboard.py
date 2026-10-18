"""Read-only governance dashboard projections. Author: Abdelhalim Talbi."""
from collections import Counter
from datetime import datetime, timezone


def dashboard_snapshot(governance):
    if not governance.verify_audit():
        raise ValueError('Audit integrity check failed')
    db = governance.db
    decisions = [dict(zip(('id','title','status','author','approver'), r)) for r in db.execute('SELECT id,title,status,author,approver FROM decisions ORDER BY id')]
    reservations = [dict(zip(('id','decision_id','description','blocking','status','owner'), r)) for r in db.execute('SELECT id,decision_id,description,blocking,status,owner FROM reservations ORDER BY id')]
    artifacts = [dict(zip(('id','kind','title','state','owner','reference'), r)) for r in db.execute('SELECT id,kind,title,state,owner,reference FROM artifacts ORDER BY id')]
    links = [dict(zip(('decision_id','artifact_id'), r)) for r in db.execute('SELECT decision_id,artifact_id FROM artifact_links ORDER BY decision_id,artifact_id')]
    counts = Counter(d['status'] for d in decisions)
    blocking = sum(bool(r['blocking']) and r['status']=='OPEN' for r in reservations)
    unfinished = sum(a['kind']=='ACTION' and a['state']!='DONE' for a in artifacts)
    missing = sum(a['kind']=='EVIDENCE' and (a['state']!='DONE' or not a['reference'].strip()) for a in artifacts)
    return {'metrics': {'decisions':len(decisions),'pending':counts['PROPOSED'],'approved':counts['APPROVED'],'blocking':blocking,'unfinished_actions':unfinished,'missing_evidence':missing}, 'decisions':decisions,'reservations':reservations,'artifacts':artifacts,'links':links,'audit_valid':True}


def graph_model(snapshot, decision_id):
    decision = next((d for d in snapshot['decisions'] if d['id']==decision_id),None)
    if decision is None: raise ValueError('Unknown decision')
    artifacts = {a['id']:a for a in snapshot['artifacts']}
    related = [artifacts[l['artifact_id']] for l in snapshot['links'] if l['decision_id']==decision_id and l['artifact_id'] in artifacts]
    reservations = [r for r in snapshot['reservations'] if r['decision_id']==decision_id]
    return {'decision':decision,'artifacts':related,'reservations':reservations}
