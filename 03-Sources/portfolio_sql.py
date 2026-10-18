"""Database-side filtered pagination. Author: Abdelhalim Talbi."""
from datetime import date

def portfolio_sql(g, as_of=None, owner='', query='', priority='TOUTES', sort='priority', limit=50, offset=0):
    today=date.fromisoformat(as_of) if as_of else date.today()
    if priority not in ('TOUTES','CRITIQUE','ATTENTION','NORMAL'): raise ValueError('Invalid priority')
    if sort not in ('priority','id','status','overdue'): raise ValueError('Invalid sort')
    if type(limit)!=int or not 1<=limit<=5000 or type(offset)!=int or offset<0: raise ValueError('Invalid pagination')
    if not g.verify_audit(): raise ValueError('Audit integrity check failed')
    db=g.db
    # Legacy writable calls may install indexes; background readers remain strictly read-only.
    if not db.execute('PRAGMA query_only').fetchone()[0]:
        for sql in (
            'CREATE INDEX IF NOT EXISTS ix_res_dec ON reservations(decision_id,status,blocking)',
            'CREATE INDEX IF NOT EXISTS ix_link_dec ON artifact_links(decision_id,artifact_id)',
            'CREATE INDEX IF NOT EXISTS ix_follow_dec ON meeting_followups(decision_id,status,due_date)',
            'CREATE INDEX IF NOT EXISTS ix_meet_dec ON meeting_decisions(decision_id,meeting_id)',
        ):
            db.execute(sql)
    cte="""WITH base AS (
      SELECT d.id,d.title,d.author,d.status,d.approver,
      (SELECT COUNT(*) FROM reservations r WHERE r.decision_id=d.id AND r.blocking=1 AND r.status='OPEN') blockers_count,
      (SELECT COUNT(*) FROM artifact_links l JOIN artifacts a ON a.id=l.artifact_id WHERE l.decision_id=d.id AND a.kind='ACTION' AND a.state!='DONE') actions_count,
      (SELECT COUNT(*) FROM meeting_followups f WHERE f.decision_id=d.id AND f.status='OPEN' AND f.due_date<:today) overdue_count
      FROM decisions d), classified AS (
      SELECT *,CASE WHEN blockers_count>0 OR overdue_count>0 THEN 'CRITIQUE' WHEN status='PROPOSED' OR actions_count>0 THEN 'ATTENTION' ELSE 'NORMAL' END priority FROM base),
      filtered AS (SELECT * FROM classified WHERE (:priority='TOUTES' OR priority=:priority)
      AND (:owner='' OR instr(lower(author),:owner)>0 OR EXISTS(SELECT 1 FROM meeting_followups f WHERE f.decision_id=classified.id AND instr(lower(f.owner),:owner)>0))
      AND (:query='' OR instr(lower(id),:query)>0 OR instr(lower(title),:query)>0 OR instr(lower(author),:query)>0 OR instr(lower(status),:query)>0))"""
    args=dict(today=today.isoformat(),priority=priority,owner=owner.strip().lower(),query=query.strip().lower(),limit=limit,offset=offset)
    metrics=db.execute(cte+" SELECT COUNT(*),COALESCE(SUM(priority='CRITIQUE'),0),COALESCE(SUM(status='PROPOSED'),0),COALESCE(SUM(overdue_count),0) FROM filtered",args).fetchone()
    order={'priority':"CASE priority WHEN 'CRITIQUE' THEN 0 WHEN 'ATTENTION' THEN 1 ELSE 2 END,id",'id':'id','status':'status,id','overdue':'overdue_count DESC,id'}[sort]
    rows=db.execute(cte+f' SELECT id,title,author,status,approver,priority,overdue_count FROM filtered ORDER BY {order} LIMIT :limit OFFSET :offset',args).fetchall()
    items=[]
    for rid,title,author,status,approver,prio,overdue in rows:
        blockers=[r[0] for r in db.execute("SELECT id FROM reservations WHERE decision_id=? AND blocking=1 AND status='OPEN' ORDER BY id",(rid,))]
        actions=[r[0] for r in db.execute("SELECT a.id FROM artifact_links l JOIN artifacts a ON a.id=l.artifact_id WHERE l.decision_id=? AND a.kind='ACTION' AND a.state!='DONE' ORDER BY a.id",(rid,))]
        committees=[r[0] for r in db.execute('SELECT meeting_id FROM meeting_decisions WHERE decision_id=? ORDER BY meeting_id',(rid,))]
        followups=[]
        for r in db.execute("SELECT id,meeting_id,decision_id,owner,due_date,description,status,evidence FROM meeting_followups WHERE decision_id=? AND status='OPEN' ORDER BY due_date,id",(rid,)):
            followups.append(dict(zip(('id','meeting_id','decision_id','owner','due_date','description','status','evidence','overdue'),(*r,r[4]<today.isoformat()))))
        items.append(dict(id=rid,title=title,author=author,status=status,approver=approver,priority=prio,overdue_count=overdue,blockers=blockers,actions=actions,committees=committees,followups=followups))
    total=metrics[0]
    return dict(as_of=today.isoformat(),items=items,metrics=dict(zip(('decisions','critical','pending','overdue'),metrics)),audit_valid=True,total_matches=total,offset=offset,page_size=limit,has_previous=offset>0,has_next=offset+limit<total,truncated=offset+limit<total)
