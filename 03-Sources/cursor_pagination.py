"""Stable keyset navigation for decision identifiers. Author: Abdelhalim Talbi."""
import base64
import json

def _encode(identifier):
    return base64.urlsafe_b64encode(json.dumps({'v':1,'after':identifier},separators=(',',':')).encode()).decode().rstrip('=')

def _decode(token):
    if not isinstance(token,str) or len(token)>4096: raise ValueError('Invalid cursor')
    try:
        raw=base64.urlsafe_b64decode(token+'='*(-len(token)%4))
        data=json.loads(raw)
        if set(data)!={'v','after'} or data['v']!=1 or not isinstance(data['after'],str):raise ValueError()
        return data['after']
    except Exception as exc:raise ValueError('Invalid cursor') from exc

def decision_page(g,limit=50,cursor=None):
    """Keyset pagination, ID ascending. Snapshot consistency across writes is not guaranteed."""
    if type(limit) is not int or not 1<=limit<=500:raise ValueError('Invalid limit')
    if not g.verify_audit():raise ValueError('Audit integrity check failed')
    after=_decode(cursor) if cursor is not None else ''
    rows=g.db.execute('SELECT id,title,status,author FROM decisions WHERE id>? ORDER BY id LIMIT ?', (after,limit+1)).fetchall()
    has_next=len(rows)>limit
    page=rows[:limit]
    return {'items':[dict(zip(('id','title','status','author'),r)) for r in page],
            'has_next':has_next,'next_cursor':_encode(page[-1][0]) if has_next and page else None,
            'page_size':limit,'audit_valid':True}
