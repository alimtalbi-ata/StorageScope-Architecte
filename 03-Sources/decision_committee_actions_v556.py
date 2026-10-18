"""Committee action register, conservative and read-only. Author: Abdelhalim Talbi."""
import json
from decision_review_v539 import review_dossier
from campaign_report_v530 import _atomic_write


def committee_actions(store, *, today=None, owner=None, status='all', deadline='all'):
    """Summarize human actions, ownership and evidence gaps; never certify evidence."""
    dossier = review_dossier(store, today=today, owner=owner, status=status, deadline=deadline)
    rows = []
    for sheet in dossier['decision_sheets']:
        gaps = []
        if not sheet['evidence_reference'].strip(): gaps.append('REFERENCE_ABSENTE')
        if not sheet['links']: gaps.append('PREUVE_LIEE_ABSENTE')
        if sheet['status'] == 'IN_REVIEW' and not sheet['approval']: gaps.append('VALIDATION_ATTENDUE')
        actions = []
        if gaps: actions.append('COMPLETER_PREUVES')
        if sheet['status'] in ('OPEN', 'IN_REVIEW'): actions.append('STATUER_EN_COMITE')
        if sheet['deadline_state'] == 'overdue': actions.append('TRAITER_RETARD')
        rows.append({'decision_id':sheet['id'],'subject':sheet['subject'],
                     'owner':sheet['owner'],'due_date':sheet['due_date'],
                     'deadline_state':sheet['deadline_state'],'priority':sheet['priority'],
                     'status':sheet['status'],'missing_evidence':gaps,
                     'expected_actions':actions,'human_decision_required':bool(actions),
                     'linked_evidence_count':len(sheet['links'])})
    return {'schema':'storagescope.committee-actions.v5.56','as_of':dossier['as_of'],
            'audit_head':dossier['audit_head'],'actions':rows,
            'human_decisions_pending':sum(x['human_decision_required'] for x in rows),
            'missing_evidence_decisions':sum(bool(x['missing_evidence']) for x in rows),
            'audit_verified':True,'evidence_sufficiency_verified':False,
            'production_activation':False,'author':'Abdelhalim Talbi'}


def export_committee_actions(store, destination, *, format='md', **filters):
    if format not in ('md','json'): raise ValueError('unsupported format')
    data=committee_actions(store,**filters)
    if format=='json': body=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    else:
        def clean(x): return str(x).replace('|','\\|').replace('\n',' ').replace('\r',' ')
        lines=['# Actions attendues — comité d’architecture','',
               f"Date : {clean(data['as_of'])} | Audit SHA256 : `{data['audit_head']}`",'',
               '| Priorité | Décision | Sujet | Responsable | Échéance | État | Preuves manquantes | Actions |',
               '|---|---|---|---|---|---|---|---|']
        for row in data['actions']:
            lines.append('| '+' | '.join(clean(v) for v in [row['priority'],row['decision_id'],row['subject'],row['owner'],row['due_date'],row['deadline_state'],', '.join(row['missing_evidence']),', '.join(row['expected_actions'])])+' |')
        lines+=['','Preuves non certifiées ; décisions humaines requises. Aucune activation en production.','','Auteur : Abdelhalim Talbi.']
        body='\n'.join(lines)+'\n'
    _atomic_write(destination,body)
    return data
