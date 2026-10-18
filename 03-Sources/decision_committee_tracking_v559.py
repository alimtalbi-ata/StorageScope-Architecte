"""Verified human committee follow-up view. Author: Abdelhalim Talbi."""
from collections import Counter
from datetime import date
from decision_committee_resolution_v558 import CommitteeResolutionStore
from decision_committee_register_v557 import action_register

def committee_tracking(store, *, owner=None, priority='ALL', deadline='ALL', today=None):
    """Read-only action list with full verified resolution history; no implicit approval."""
    register=action_register(store,owner=owner,priority=priority,deadline=deadline,today=today)
    ledger=CommitteeResolutionStore(store.path).resolutions()
    grouped={}
    for entry in ledger:
        grouped.setdefault(entry['decision_id'],[]).append(entry)
    rows=[]
    for action in register['actions']:
        history=grouped.get(action['decision_id'],[])
        latest=history[-1] if history else None
        rows.append({**action,'committee_verdict':latest['verdict'] if latest else 'UNREVIEWED',
                     'committee_actor':latest['actor'] if latest else None,
                     'committee_meeting_date':latest['meeting_date'] if latest else None,
                     'committee_audit_seq':latest['audit_seq'] if latest else None,
                     'committee_history':history,
                     'deferred':bool(latest and latest['verdict']=='DEFER'),
                     'production_activation':False})
    counts=Counter(r['committee_verdict'] for r in rows)
    return {'schema':'storagescope.committee-tracking.v5.59','actions':rows,
            'total':len(rows),'verdict_counts':dict(sorted(counts.items())),
            'deferred':counts['DEFER'],'unreviewed':counts['UNREVIEWED'],
            'audit_head':register['audit_head'],'production_activation':False,
            'author':'Abdelhalim Talbi'}
