"""Bounded SQL read models for responsive Tk dashboard. Abdelhalim Talbi."""

def summary_metrics(db):
    statuses = dict(db.execute('SELECT status, COUNT(*) FROM decisions GROUP BY status'))
    blocking = db.execute("SELECT COUNT(*) FROM reservations WHERE blocking=1 AND status='OPEN'").fetchone()[0]
    unfinished = db.execute("SELECT COUNT(*) FROM artifacts WHERE kind='ACTION' AND state!='DONE'").fetchone()[0]
    missing = db.execute("SELECT COUNT(*) FROM artifacts WHERE kind='EVIDENCE' AND (state!='DONE' OR TRIM(COALESCE(reference,''))='')").fetchone()[0]
    return dict(decisions=sum(statuses.values()),pending=statuses.get('PROPOSED',0),approved=statuses.get('APPROVED',0),blocking=blocking,unfinished_actions=unfinished,missing_evidence=missing)


def decision_graph(db, decision_id, limit=None):
    """Indexed read model; optional bounded fetch for very large dependency sets."""
    if limit is not None and (type(limit) is not int or not 1 <= limit <= 100000):
        raise ValueError("Invalid graph limit")
    row=db.execute('SELECT id,title,status,author,approver FROM decisions WHERE id=?',(decision_id,)).fetchone()
    if row is None: raise ValueError('Unknown decision')
    sql_r='SELECT id,decision_id,description,blocking,status,owner FROM reservations WHERE decision_id=? ORDER BY id'
    args_r=(decision_id,)
    if limit is not None: sql_r+=' LIMIT ?'; args_r+=(limit,)
    reservations=[dict(zip(('id','decision_id','description','blocking','status','owner'),r)) for r in db.execute(sql_r,args_r)]
    sql_a='SELECT a.id,a.kind,a.title,a.state,a.owner,a.reference FROM artifact_links l JOIN artifacts a ON a.id=l.artifact_id WHERE l.decision_id=? ORDER BY a.id'
    args_a=(decision_id,)
    if limit is not None: sql_a+=' LIMIT ?'; args_a+=(limit,)
    artifacts=[dict(zip(('id','kind','title','state','owner','reference'),r)) for r in db.execute(sql_a,args_a)]
    return {'decision':dict(zip(('id','title','status','author','approver'),row)),'reservations':reservations,'artifacts':artifacts}


def bounded_rows(db, table, limit=250):
    if not isinstance(limit,int) or not 1 <= limit <= 1000: raise ValueError('Invalid display limit')
    sql={
      'decisions': "SELECT id,title,status,author,COALESCE(approver,'') FROM decisions ORDER BY created_at DESC,id DESC LIMIT ?",
      'reservations': 'SELECT id,decision_id,description,blocking,status,owner FROM reservations ORDER BY id LIMIT ?',
      'artifacts': 'SELECT id,kind,title,state,owner,reference FROM artifacts ORDER BY id LIMIT ?',
      'meetings': 'SELECT id,title,scheduled_at,chair,status FROM meetings ORDER BY scheduled_at DESC,id DESC LIMIT ?',
    }
    if table not in sql: raise ValueError('Invalid table')
    return list(db.execute(sql[table],(limit,)))


def find_decisions(db, query, limit=30):
    """Bounded, parameterized search across the entire decision register."""
    if not isinstance(query,str): raise ValueError('Query must be text')
    if not isinstance(limit,int) or isinstance(limit,bool) or not 1 <= limit <= 100: raise ValueError('Invalid limit')
    q=query.strip()
    if not q: return []
    # Escape LIKE wildcards so the user searches literal text.
    escaped=q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
    pattern='%'+escaped+'%'
    return [dict(zip(('id','title','status','author'),row)) for row in db.execute(
        "SELECT id,title,status,author FROM decisions WHERE id LIKE ? ESCAPE '\\' OR title LIKE ? ESCAPE '\\' OR author LIKE ? ESCAPE '\\' ORDER BY CASE WHEN id=? THEN 0 WHEN id LIKE ? ESCAPE '\\' THEN 1 ELSE 2 END,id LIMIT ?",
        (pattern,pattern,pattern,q,escaped+'%',limit))]
