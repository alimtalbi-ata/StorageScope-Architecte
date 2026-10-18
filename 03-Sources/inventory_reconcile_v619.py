"""StorageScope v6.19: explainable, non-destructive multi-source reconciliation."""
from __future__ import annotations
import argparse
import collections
import json
from pathlib import Path

IDENTITY_FIELDS = ('serial', 'wwn', 'uuid')

def reconcile(records):
    """Return candidate duplicates and attribute conflicts; never mutate inputs."""
    if not isinstance(records, list):
        raise ValueError('Inventory must be a JSON array')
    groups = collections.defaultdict(list)
    invalid = []
    for index, item in enumerate(records):
        if not isinstance(item, dict):
            invalid.append({'index': index, 'reason': 'not_object'})
            continue
        source = item.get('source')
        if not isinstance(source, str) or not source.strip():
            invalid.append({'index': index, 'reason': 'missing_source'})
        for field in IDENTITY_FIELDS:
            val = item.get(field)
            if isinstance(val, str) and val.strip():
                groups[(field, val.strip().casefold())].append(index)
    pairs = collections.defaultdict(set)
    for (field, value), indices in groups.items():
        if len(indices) < 2:
            continue
        for pos, left in enumerate(indices):
            for right in indices[pos + 1:]:
                pairs[(left, right)].add(field)
    candidates = []
    for (left, right), evidence in sorted(pairs.items()):
        a, b = records[left], records[right]
        conflicts = []
        for field in sorted((set(a) & set(b)) - set(IDENTITY_FIELDS) - {'source', 'updated_at'}):
            if a[field] is not None and b[field] is not None and a[field] != b[field]:
                conflicts.append({'field': field, 'left': a[field], 'right': b[field]})
        candidates.append({'indices': [left, right], 'identity_evidence': sorted(evidence),
                           'sources': [a.get('source'), b.get('source')],
                           'conflicts': conflicts, 'action': 'REVIEW_REQUIRED'})
    return {'schema': 'storagescope.reconciliation.v1', 'records': len(records),
            'candidate_count': len(candidates), 'candidates': candidates,
            'invalid_records': invalid, 'automatic_merges': 0, 'destructive_changes': 0}

def main(argv=None):
    parser = argparse.ArgumentParser(description='Read-only CMDB reconciliation')
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    report = reconcile(json.loads(args.input.read_text(encoding='utf-8')))
    content = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(content, encoding='utf-8')
    else:
        print(content, end='')
    return 0 if not report['invalid_records'] else 2

if __name__ == '__main__':
    raise SystemExit(main())
