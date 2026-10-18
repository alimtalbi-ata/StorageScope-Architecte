"""Canonical, read-only governance service for StorageScope 6.24.

Bridges legacy quality/reconciliation output to stable review identities.
No database mutation or automatic merging occurs here.
"""
from __future__ import annotations
import copy
from governance_report_v620 import build_report
from review_registry_v622 import candidate_key

ID_FIELDS = ('asset_id', 'ci_id', 'id')

def stable_id(record):
    if not isinstance(record, dict):
        return None
    for field in ID_FIELDS:
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None

def inspect(records):
    if not isinstance(records, list):
        raise ValueError('Inventory must be a list')
    report = copy.deepcopy(build_report(records))
    for candidate in report['reconciliation']['candidates']:
        indices = candidate['indices']
        ids = [stable_id(records[i]) for i in indices]
        if all(ids) and len({v.casefold() for v in ids}) == 2:
            candidate['asset_ids'] = ids
            candidate['review_key'] = candidate_key(candidate)
            candidate['review_eligibility'] = 'ELIGIBLE'
        else:
            candidate['asset_ids'] = ids
            candidate['review_key'] = None
            candidate['review_eligibility'] = 'MISSING_OR_AMBIGUOUS_STABLE_ID'
        candidate['action'] = 'REVIEW_REQUIRED'
    report['schema'] = 'storagescope.governance.v2'
    report['review_eligible'] = sum(c['review_key'] is not None for c in report['reconciliation']['candidates'])
    report['automatic_merges'] = 0
    return report
