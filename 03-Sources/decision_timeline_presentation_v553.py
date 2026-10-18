"""Fail-closed chronological evidence presentation. Author: Abdelhalim Talbi."""
from decision_evidence_navigation_v552 import evidence_event_navigation

STATUS = {'CURRENT': ('Qualification actuelle', '#246e56'),
          'STALE': ('Preuves modifiées — requalification requise', '#a62d37'),
          'UNREVIEWED': ('Aucune qualification humaine', '#a96912'),
          'HISTORICAL': ('Qualification historique', '#666666'),
          'EVENT': ('Événement', '#34465a')}

def timeline_presentation(store, ident):
    """Build a verified UI projection; never infer sufficiency from linked evidence."""
    navigation = evidence_event_navigation(store, ident)
    events = navigation['events']
    qualifications = [e for e in events if e['type'] == 'EVIDENCE_QUALIFIED']
    latest_seq = qualifications[-1]['sequence'] if qualifications else None
    rows = []
    for e in events:
        if e['type'] == 'EVIDENCE_QUALIFIED':
            state = ('STALE' if e['qualification_stale'] else 'CURRENT') if e['sequence'] == latest_seq else 'HISTORICAL'
        else:
            state = 'EVENT'
        rows.append({**e, 'state':state, 'state_label':STATUS[state][0], 'color':STATUS[state][1]})
    current = 'UNREVIEWED' if latest_seq is None else rows[next(i for i,r in enumerate(rows) if r['sequence']==latest_seq)]['state']
    if current == 'CURRENT' and navigation['requires_requalification']:
        # Historical stale qualifications do not invalidate a newer review.
        pass
    return {'decision_id':ident, 'audit_head':navigation['audit_head'], 'events':rows,
            'current_state':current, 'current_label':STATUS[current][0],
            'review_count':len(qualifications), 'production_activation':False,
            'evidence_sufficiency_verified':False, 'author':'Abdelhalim Talbi'}
