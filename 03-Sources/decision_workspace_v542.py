"""Fail-closed searchable governance workspace model. Author: Abdelhalim Talbi."""
from collections import Counter
from decision_integrity_v540 import verified_review


def workspace(store, *, query='', owner=None, status='all', deadline='all', today=None):
    if not isinstance(query, str) or len(query) > 256:
        raise ValueError('invalid search query')
    review = verified_review(store, today=today, owner=owner, status=status, deadline=deadline)
    needle = query.strip().casefold()
    sheets = [s for s in review['decision_sheets'] if not needle or any(
        needle in str(s.get(k, '')).casefold() for k in ('id','subject','owner','status','evidence_reference','rationale'))]
    sheets.sort(key=lambda d: (int(d['priority'][1]), d['due_date'], d['id']))
    counters = Counter(d['priority'] for d in sheets)
    return {'schema':'storagescope.decision-workspace.v5.42',
            'filters':{**review['filters'],'query':query},
            'global_kpis':review['global_kpis'],
            'visible_kpis':{'count':len(sheets),'p1':counters['P1'],'p2':counters['P2'],
                            'needs_review':sum(bool(s['requires_human_review']) for s in sheets)},
            'decision_sheets':sheets,'audit_head':review['audit_head'],
            'consistency_verified':True,'evidence_sufficiency_verified':False,
            'recommendation_only':True,'production_activation':False,'author':'Abdelhalim Talbi'}
