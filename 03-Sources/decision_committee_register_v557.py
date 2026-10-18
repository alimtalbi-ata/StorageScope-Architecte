"""Filtered committee action view. Author: Abdelhalim Talbi."""
import csv
import io
import json
from collections import Counter
from decision_committee_actions_v556 import committee_actions
from campaign_report_v530 import _atomic_write

PRIORITIES = ('ALL', 'P1', 'P2', 'P3')
DEADLINES = ('ALL', 'overdue', 'due_soon', 'upcoming', 'none')

def action_register(store, *, owner=None, priority='ALL', deadline='ALL', status='all', today=None):
    if priority not in PRIORITIES or deadline not in DEADLINES:
        raise ValueError('invalid committee filter')
    if owner is not None and (not isinstance(owner, str) or not owner.strip()):
        raise ValueError('invalid owner filter')
    # Integrity validation always precedes filtering, and never relies on the visible subset.
    base = committee_actions(store, today=today, status=status)
    rows = [dict(r) for r in base['actions'] if
            (owner is None or r['owner'] == owner) and
            (priority == 'ALL' or r['priority'] == priority) and
            (deadline == 'ALL' or r['deadline_state'] == deadline)]
    rows.sort(key=lambda r: (dict(P1=0,P2=1,P3=2).get(r['priority'],3),
                             r['due_date'], r['decision_id']))
    counts = Counter(r['status'] for r in rows)
    return {'schema':'storagescope.committee-register.v5.57',
            'filters':{'owner':owner,'priority':priority,'deadline':deadline,'status':status},
            'as_of':base['as_of'],'audit_head':base['audit_head'],
            'actions':rows,'total':len(rows),'pending':sum(r['human_decision_required'] for r in rows),
            'decision_status_counts':dict(sorted(counts.items())),
            'human_committee_resolution_recorded':False,
            'audit_verified':True,'production_activation':False,'author':'Abdelhalim Talbi'}

def export_action_register(store, destination, *, format='csv', **filters):
    if format not in ('csv','json'): raise ValueError('unsupported format')
    result=action_register(store,**filters)
    if format=='json': body=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    else:
        output=io.StringIO(newline='')
        fields=('decision_id','subject','owner','priority','status','due_date','deadline_state',
                'human_decision_required','missing_evidence','expected_actions','audit_head')
        writer=csv.DictWriter(output,fieldnames=fields,extrasaction='ignore');writer.writeheader()
        for row in result['actions']:
            writer.writerow({**row,'missing_evidence':'; '.join(row['missing_evidence']),
                             'expected_actions':'; '.join(row['expected_actions']),
                             'audit_head':result['audit_head']})
        body=output.getvalue()
    _atomic_write(destination,body)
    return result
