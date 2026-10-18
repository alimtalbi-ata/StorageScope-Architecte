"""Cross-domain governance overview, read-only. Author: Abdelhalim Talbi."""
from datetime import date
from dashboard import dashboard_snapshot
from committee_calendar import CommitteeCalendar

def portfolio_snapshot(governance, planning, as_of=None, owner='', query='', priority='TOUTES', sort='priority', limit=500, offset=0):
    import sqlite3
    if isinstance(governance.db, sqlite3.Connection):
        from portfolio_sql import portfolio_sql
        return portfolio_sql(governance, as_of, owner, query, priority, sort, limit, offset)
    today=date.fromisoformat(as_of) if as_of else date.today()
    snapshot=dashboard_snapshot(governance)
    calendar=CommitteeCalendar(planning).snapshot(today.isoformat(),30)
    owner=owner.strip().casefold()
    decisions={d['id']:dict(d, blockers=[], actions=[], committees=[], followups=[]) for d in snapshot['decisions']}
    for r in snapshot['reservations']:
        if r['decision_id'] in decisions and r['blocking'] and r['status']=='OPEN':
            decisions[r['decision_id']]['blockers'].append(r['id'])
    linked={}
    for link in snapshot['links']:
        linked.setdefault(link['decision_id'],set()).add(link['artifact_id'])
    for a in snapshot['artifacts']:
        if a['kind']=='ACTION' and a['state']!='DONE':
            for did,ids in linked.items():
                if a['id'] in ids and did in decisions: decisions[did]['actions'].append(a['id'])
    for mid,did in governance.db.execute('SELECT meeting_id,decision_id FROM meeting_decisions ORDER BY meeting_id,decision_id'):
        if did in decisions: decisions[did]['committees'].append(mid)
    for f in calendar['followups']:
        if f['decision_id'] in decisions: decisions[f['decision_id']]['followups'].append(f)
    query=query.strip().casefold()
    if priority not in ('TOUTES','CRITIQUE','ATTENTION','NORMAL'): raise ValueError('Filtre de priorité invalide')
    if sort not in ('priority','id','status','overdue'): raise ValueError('Tri invalide')
    if not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=5000: raise ValueError('Limite invalide')
    if not isinstance(offset,int) or isinstance(offset,bool) or offset<0: raise ValueError('Décalage invalide')
    items=[]
    for d in decisions.values():
        if owner and owner not in d['author'].casefold() and not any(owner in f['owner'].casefold() for f in d['followups']): continue
        overdue=sum(f['overdue'] for f in d['followups'])
        d['priority']='CRITIQUE' if d['blockers'] or overdue else 'ATTENTION' if d['status']=='PROPOSED' or d['actions'] else 'NORMAL'
        d['overdue_count']=overdue
        if query and query not in ' '.join([d['id'],d.get('title',''),d['author'],d['status']]).casefold(): continue
        if priority!='TOUTES' and d['priority']!=priority: continue
        items.append(d)
    rank={'CRITIQUE':0,'ATTENTION':1,'NORMAL':2}
    items.sort(key={'priority':lambda d:(rank[d['priority']],d['id']),'id':lambda d:(d['id'],),'status':lambda d:(d['status'],d['id']),'overdue':lambda d:(-d['overdue_count'],d['id'])}[sort])
    total=len(items)
    page=items[offset:offset+limit]
    return {'as_of':today.isoformat(),'items':page,'metrics':{'decisions':total,'critical':sum(d['priority']=='CRITIQUE' for d in items),'pending':sum(d['status']=='PROPOSED' for d in items),'overdue':sum(d['overdue_count'] for d in items)},'audit_valid':True,'total_matches':total,'offset':offset,'page_size':limit,'has_previous':offset>0,'has_next':offset+limit<total,'truncated':offset+limit<total}
