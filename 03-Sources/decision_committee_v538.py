"""Read-only architecture committee agenda and governance filters. Author: Abdelhalim Talbi."""
from collections import Counter
from datetime import date
import csv
import io
import json
from pathlib import Path
from campaign_report_v530 import _atomic_write

STATES = frozenset(('all','overdue','due_today','upcoming','closed'))
STATUSES = frozenset(('all','OPEN','IN_REVIEW','APPROVED','REJECTED','CLOSED'))


def committee_dashboard(store, *, today=None, owner=None, status='all', deadline='all'):
    if status not in STATUSES or deadline not in STATES:
        raise ValueError('invalid governance filter')
    if owner is not None and (not isinstance(owner,str) or not owner.strip()):
        raise ValueError('invalid owner filter')
    report = store.governance_report(today=today)  # fail closed on broken audit chain
    decisions = [d for d in report['decisions'] if
                 (owner is None or d['owner'].casefold()==owner.strip().casefold()) and
                 (status=='all' or d['status']==status) and
                 (deadline=='all' or d['deadline_state']==deadline)]
    def priority(d):
        if d['deadline_state']=='overdue': return 'P1'
        if d['deadline_state']=='due_today': return 'P2'
        if d['status']=='IN_REVIEW' or not d['linked_events']: return 'P2'
        return 'P3'
    agenda=[]
    for d in decisions:
        reasons=[]
        if d['deadline_state']=='overdue': reasons.append('Échéance dépassée')
        if d['deadline_state']=='due_today': reasons.append('Échéance du jour')
        if not d['linked_events']: reasons.append('Aucune alerte liée')
        if d['status']=='IN_REVIEW': reasons.append('Validation attendue')
        agenda.append({'id':d['id'],'subject':d['subject'],'owner':d['owner'],
                       'status':d['status'],'due_date':d['due_date'],
                       'deadline_state':d['deadline_state'],'priority':priority(d),
                       'reasons':reasons,'linked_events':d['linked_events'],
                       'followup_recorded':d['followup_recorded']})
    agenda.sort(key=lambda x: (int(x['priority'][1]),x['due_date'],x['id']))
    return {'schema':'storagescope.committee.v5.38','as_of':report['as_of'],
            'filters':{'owner':owner,'status':status,'deadline':deadline},
            'global_kpis':report['kpis'], 'filtered_kpis':{'count':len(agenda),
              'by_status':dict(Counter(x['status'] for x in agenda)),
              'by_priority':dict(Counter(x['priority'] for x in agenda))},
            'agenda':agenda,'audit_head':report['audit_head'],
            'audit_verified':True,'recommendation_only':True,
            'production_activation':False,'author':'Abdelhalim Talbi'}


def export_committee(store, destination, *, format='md', **filters):
    if format not in ('md','json','csv'): raise ValueError('unsupported export format')
    data=committee_dashboard(store,**filters)
    if format=='json': content=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    elif format=='csv':
        out=io.StringIO(); w=csv.writer(out)
        w.writerow(['priority','id','subject','owner','status','due_date','deadline_state','linked_events','reasons'])
        for x in data['agenda']:
            w.writerow([x[k] if k!='reasons' else '; '.join(x[k]) for k in ('priority','id','subject','owner','status','due_date','deadline_state','linked_events','reasons')])
        content=out.getvalue()
    else:
        content='# Ordre du jour — comité d’architecture\n\n'
        content+=f"Date : {data['as_of']} | Empreinte audit : `{data['audit_head']}`\n\n"
        content+='| Priorité | Décision | Responsable | Statut | Échéance | Motifs |\n|---|---|---|---|---|---|\n'
        for x in data['agenda']:
            safe=lambda s:str(s).replace('|','\\|').replace('\n',' ')
            content+='| '+' | '.join(map(safe,[x['priority'],x['id'],x['owner'],x['status'],x['due_date'],', '.join(x['reasons'])]))+' |\n'
        content+='\n*Recommandations uniquement — aucune activation en production.*\n'
    _atomic_write(destination,content)
    return data
