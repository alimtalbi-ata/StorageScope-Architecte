"""Verified read-only navigation between audit events and evidence references.
Author: Abdelhalim Talbi. No production activation.
"""
from decision_timeline_visual_v551 import visual_timeline
from decision_qualification_v547 import QualificationStore


def evidence_event_navigation(store, ident):
    """Reject mismatched audit snapshots; mark stale reviews without trusting them."""
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError('invalid decision identifier')
    timeline = visual_timeline(store, ident)
    audit_head = timeline['audit_head']
    qualification_store = QualificationStore(store.path)
    qualifications = qualification_store.qualifications(ident)
    # Guard against concurrent writes between the separate read-only snapshots.
    if store.report()['audit_head'] != audit_head:
        raise ValueError('audit changed during evidence navigation')
    by_seq = {q['audit_seq']: q for q in qualifications}
    events = []
    for event in timeline['events']:
        details = event['details']
        seq = event['sequence']
        evidence_id = details.get('evidence_id') if event['type'] == 'EVIDENCE_LINKED' else None
        reference = details.get('evidence') if event['type'] == 'CREATED' else None
        q = by_seq.get(seq)
        events.append({'sequence':seq,'type':event['type'],'label':event['label'],
                       'evidence_id':evidence_id,'reference':reference,
                       'qualification_verdict':q['verdict'] if q else None,
                       'qualification_stale':q['stale'] if q else None,
                       'audit_hash':None, 'production_activation':False})
    qualification_events = {e['sequence'] for e in events if e['type']=='EVIDENCE_QUALIFIED'}
    if qualification_events != set(by_seq):
        raise ValueError('qualification navigation mismatch')
    return {'decision_id':ident,'audit_head':audit_head,'events':events,
            'requires_requalification':any(q['stale'] for q in qualifications),
            'unreviewed':not qualifications,'recommendation_only':True,
            'production_activation':False,'author':'Abdelhalim Talbi'}
