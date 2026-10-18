"""Safe display model for chronological governance review. Author: Abdelhalim Talbi."""
from decision_chronology_v550 import decision_chronology
from decision_qualification_v547 import QualificationStore


def visual_timeline(store, ident):
    """Read-only ordered timeline; refuse inconsistent or orphaned qualification records."""
    timeline = decision_chronology(store, ident)
    qualifications = QualificationStore(store.path).qualifications()
    by_sequence = {q['audit_seq']: q for q in qualifications}
    events = []
    for event in timeline['events']:
        seq = event['sequence']
        qualification = by_sequence.get(seq)
        if event['type'] == 'EVIDENCE_QUALIFIED' and qualification is None:
            raise ValueError('missing qualification in timeline')
        if qualification is not None and (event['type'] != 'EVIDENCE_QUALIFIED' or qualification['decision_id'] != ident):
            raise ValueError('qualification timeline mismatch')
        events.append({'sequence':seq,'label':event['label'],'type':event['type'],
                       'actor':event['details'].get('actor',''),
                       'verdict':qualification['verdict'] if qualification else None,
                       'stale':qualification['stale'] if qualification else None,
                       'details':event['details']})
    if any(a['sequence'] >= b['sequence'] for a,b in zip(events,events[1:])):
        raise ValueError('timeline ordering failure')
    return {'decision_id':ident,'events':events,'audit_head':timeline['audit_head'],
            'production_activation':False,'recommendation_only':True,'author':'Abdelhalim Talbi'}
