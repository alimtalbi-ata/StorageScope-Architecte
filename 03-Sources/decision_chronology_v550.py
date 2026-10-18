"""Human-readable verified decision event timeline. Author: Abdelhalim Talbi."""
from decision_integrity_v540 import consistency_report

LABELS = {'CREATED':'Création', 'TRANSITION':'Changement de statut',
          'EVIDENCE_LINKED':'Preuve liée', 'FOLLOWUP_RECORDED':'Relance',
          'EVIDENCE_QUALIFIED':'Qualification humaine', 'COMMITTEE_RESOLVED':'Décision de comité'}

def decision_chronology(store, ident):
    checked = consistency_report(store)
    if not checked['consistent']:
        raise ValueError('decision consistency failure')
    report = store.report()
    if ident not in {d['id'] for d in report['decisions']}:
        raise KeyError(ident)
    events = [a for a in report['audit'] if a['decision_id'] == ident]
    return {'decision_id': ident, 'audit_head': report['audit_head'],
            'events': [{'sequence':a['seq'], 'type':a['event']['event'],
                        'label':LABELS[a['event']['event']], 'details':a['event']} for a in events],
            'recommendation_only':True, 'production_activation':False,
            'author':'Abdelhalim Talbi'}
