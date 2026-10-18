"""Consolidated, read-only committee dashboard and export. Author: Abdelhalim Talbi."""
import csv
import io
import json
from collections import Counter
from datetime import date
from decision_committee_tracking_v559 import committee_tracking
from campaign_report_v530 import _atomic_write

VERDICTS=('ALL','APPROVE','REJECT','DEFER','UNREVIEWED')
DEADLINES=('ALL','overdue','due_soon','upcoming','none')
PRIORITIES=('ALL','P1','P2','P3')

def committee_dashboard_v560(store, *, owner=None, priority='ALL', deadline='ALL', verdict='ALL', today=None):
    if verdict not in VERDICTS or priority not in PRIORITIES or deadline not in DEADLINES:
        raise ValueError('invalid committee dashboard filter')
    # Validate entire audit and resolution ledger before applying any display filters.
    base=committee_tracking(store,today=today)
    rows=[r for r in base['actions'] if
          (owner is None or r['owner']==owner) and
          (priority=='ALL' or r['priority']==priority) and
          (deadline=='ALL' or r['deadline_state']==deadline) and
          (verdict=='ALL' or r['committee_verdict']==verdict)]
    counts=Counter(r['committee_verdict'] for r in rows)
    return {'schema':'storagescope.committee-dashboard.v5.60',
            'filters':{'owner':owner,'priority':priority,'deadline':deadline,'verdict':verdict},
            'audit_head':base['audit_head'],'total':len(rows),
            'overdue':sum(r['deadline_state']=='overdue' for r in rows),
            'deferred':counts['DEFER'],'unreviewed':counts['UNREVIEWED'],
            'verdict_counts':dict(sorted(counts.items())), 'actions':rows,
            'production_activation':False,'author':'Abdelhalim Talbi'}

def export_committee_dashboard(store,destination,*,format='csv',**filters):
    if format not in ('csv','json'):raise ValueError('unsupported format')
    data=committee_dashboard_v560(store,**filters)
    if format=='json':body=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    else:
        output=io.StringIO(newline='')
        columns=('decision_id','owner','priority','due_date','deadline_state','committee_verdict',
                 'committee_actor','committee_meeting_date','committee_audit_seq','missing_evidence',
                 'expected_actions','audit_head')
        writer=csv.DictWriter(output,fieldnames=columns,extrasaction='ignore')
        writer.writeheader()
        for row in data['actions']:
            writer.writerow({**row,'missing_evidence':'; '.join(row['missing_evidence']),
                             'expected_actions':'; '.join(row['expected_actions']),
                             'audit_head':data['audit_head']})
        body=output.getvalue()
    _atomic_write(destination,body)
    return data
