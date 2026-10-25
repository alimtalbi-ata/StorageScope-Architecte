"""Explainable, read-only multi-source inventory/CMDB reconciliation.

V6.197 hardens the V6.19 contract: missing provenance and contradictory
strong identifiers must never become automatic matches.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

IDENTITY_FIELDS = ('serial', 'wwn', 'uuid')
UNKNOWN_IDENTITIES = frozenset({'unknown', 'n/a', 'na', 'none', 'null', 'not available', '-'})
MAX_RECORDS = 10000
MAX_CANDIDATE_PAIRS = 50000
ASSET_KIND_ALIASES = {'array': 'storage_array', 'storage': 'storage_array',
                      'switch': 'san_switch', 'server': 'host'}


def _identity(value):
    """Normalize identity evidence, without treating placeholders as keys."""
    if not isinstance(value, str):
        return None
    normalized = value.strip().casefold()
    return normalized if normalized and normalized not in UNKNOWN_IDENTITIES else None


def _asset_kind(item):
    """Resolve optional kind/type evidence; reject contradictory self-descriptions."""
    observed = []
    for field in ('kind', 'type'):
        value = item.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            return None, 'invalid_asset_kind'
        normalized = value.strip().casefold().replace('-', '_').replace(' ', '_')
        observed.append(ASSET_KIND_ALIASES.get(normalized, normalized))
    if len(set(observed)) > 1:
        return None, 'conflicting_asset_kind'
    return (observed[0] if observed else None), None


def _manufacturer(item):
    """Canonicalize vendor/manufacturer evidence without guessing vendor aliases.

    Missing or explicitly unknown values remain unknown. Two contradictory
    descriptions on one record make that record untrustworthy for matching.
    """
    observed = []
    for field in ('manufacturer', 'vendor'):
        value = item.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            return None, 'invalid_manufacturer'
        normalized = ' '.join(value.split()).casefold()
        if normalized not in UNKNOWN_IDENTITIES:
            observed.append(normalized)
    if len(set(observed)) > 1:
        return None, 'conflicting_manufacturer'
    return (observed[0] if observed else None), None


def reconcile(records):
    """Return review-only candidates with provenance and identity conflicts.

    Invalid provenance cannot participate in identity matching. A match on one
    strong identifier with contradictory other strong IDs is quarantined.
    Never modifies records or writes to a CMDB.
    """
    if not isinstance(records, list):
        raise ValueError('Inventory must be a JSON array')
    if len(records) > MAX_RECORDS:
        raise ValueError(f'Inventory exceeds {MAX_RECORDS} records')

    groups = collections.defaultdict(list)
    invalid = []
    identities = {}
    asset_kinds = {}
    manufacturers = {}
    for index, item in enumerate(records):
        if not isinstance(item, dict):
            invalid.append({'index': index, 'reason': 'not_object'})
            continue
        source = item.get('source')
        if not isinstance(source, str) or not source.strip():
            invalid.append({'index': index, 'reason': 'missing_source'})
            continue  # Fail closed: unprovenanced records are not match evidence.
        kind, kind_error = _asset_kind(item)
        if kind_error:
            invalid.append({'index': index, 'reason': kind_error})
            continue  # An internally contradictory type cannot be match evidence.
        manufacturer, manufacturer_error = _manufacturer(item)
        if manufacturer_error:
            invalid.append({'index': index, 'reason': manufacturer_error})
            continue  # Untrusted manufacturer cannot become identity evidence.
        # A supplied but non-string strong ID is malformed evidence, not an
        # absent ID. Silently discarding it could let another matching field
        # conceal a contradictory or incorrectly serialized identifier.
        invalid_field = next((field for field in IDENTITY_FIELDS
                              if item.get(field) is not None and
                              not isinstance(item[field], str)), None)
        if invalid_field is not None:
            invalid.append({'index': index, 'reason': f'invalid_identity_type:{invalid_field}'})
            continue  # Fail closed; do not use any other ID from this record.
        asset_kinds[index] = kind
        manufacturers[index] = manufacturer
        strong = {field: _identity(item.get(field)) for field in IDENTITY_FIELDS}
        identities[index] = strong
        if not any(strong.values()):
            invalid.append({'index': index, 'reason': 'missing_strong_identity'})
            continue
        for field, value in strong.items():
            if value is not None:
                groups[(field, value)].append(index)

    # Invalid observations are never candidates. Their well-typed strong IDs
    # can only contaminate a valid identity component, not provide match proof.
    invalid_identity_groups = collections.defaultdict(set)
    for entry in invalid:
        index = entry['index']
        item = records[index]
        if not isinstance(item, dict):
            continue
        for field in IDENTITY_FIELDS:
            value = _identity(item.get(field))
            if value is not None:
                invalid_identity_groups[(field, value)].add(index)
    invalid_identity_link_indices = set()
    invalid_identity_origin_indices = set()
    for key, valid_indices in groups.items():
        if key in invalid_identity_groups:
            invalid_identity_link_indices.update(valid_indices)
            invalid_identity_origin_indices.update(invalid_identity_groups[key])

    pairs = collections.defaultdict(set)
    for (field, _value), indices in sorted(groups.items()):
        if len(indices) < 2:
            continue
        for pos, left in enumerate(indices):
            for right in indices[pos + 1:]:
                pairs[(left, right)].add(field)
                if len(pairs) > MAX_CANDIDATE_PAIRS:
                    raise ValueError(f'Reconciliation exceeds {MAX_CANDIDATE_PAIRS} candidate pairs')

    candidates = []
    direct_conflicts = set()
    duplicate_source_indices = set()
    adjacency = collections.defaultdict(set)
    for (left, right), evidence in sorted(pairs.items()):
        a, b = records[left], records[right]
        conflicts = []
        for field in sorted((set(a) & set(b)) - set(IDENTITY_FIELDS) - {'source', 'updated_at', 'collected_at'}):
            if a[field] is not None and b[field] is not None and a[field] != b[field]:
                conflicts.append({'field': field, 'left': a[field], 'right': b[field]})
        identity_conflicts = []
        for field in IDENTITY_FIELDS:
            av, bv = identities[left][field], identities[right][field]
            if av is not None and bv is not None and av != bv:
                identity_conflicts.append({'field': field, 'left': av, 'right': bv})
        # A shared serial/WWN/UUID cannot reconcile a NAS with a host or
        # switch. Missing kind remains unknown, never inferred.
        ak, bk = asset_kinds[left], asset_kinds[right]
        if ak is not None and bk is not None and ak != bk:
            identity_conflicts.append({'field': 'asset_kind', 'left': ak, 'right': bk})
        # A serial/WWN/UUID can be reused across different manufacturers.
        # Contradictory known manufacturer evidence is a strong identity
        # conflict, not merely a non-blocking descriptive discrepancy.
        am, bm = manufacturers[left], manufacturers[right]
        if am is not None and bm is not None and am != bm:
            identity_conflicts.append({'field': 'manufacturer', 'left': am, 'right': bm})
        # Repeated strong identity from the SAME collector is not independent
        # reconciliation evidence. Quarantine its connected identity component.
        same_source_duplicate = a['source'].strip().casefold() == b['source'].strip().casefold()
        adjacency[left].add(right)
        adjacency[right].add(left)
        if same_source_duplicate:
            duplicate_source_indices.update((left, right))
        if identity_conflicts or same_source_duplicate:
            direct_conflicts.update((left, right))
        candidates.append({
            'indices': [left, right],
            'identity_evidence': sorted(evidence),
            'sources': [a['source'], b['source']],
            'provenance': [
                {'index': i, 'source': item['source'], 'collected_at': item.get('collected_at')}
                for i, item in ((left, a), (right, b))
            ],
            'identity_conflicts': identity_conflicts,
            'same_source_duplicate': same_source_duplicate,
            'conflicts': conflicts,
            'action': ('QUARANTINE_IDENTITY_CONFLICT' if identity_conflicts else
                       'QUARANTINE_DUPLICATE_SOURCE_OBSERVATION' if same_source_duplicate
                       else 'REVIEW_REQUIRED'),
        })

    # Propagate direct conflicts and invalid links across valid-only pairs.
    # Invalid records never become nodes in the candidate graph.
    def connected_component(seeds):
        seen = set(seeds)
        pending = collections.deque(sorted(seeds))
        while pending:
            index = pending.popleft()
            for neighbor in sorted(adjacency[index]):
                if neighbor not in seen:
                    seen.add(neighbor)
                    pending.append(neighbor)
        return seen

    invalid_linked_component = connected_component(invalid_identity_link_indices)
    quarantined = connected_component(direct_conflicts) | invalid_linked_component
    for candidate in candidates:
        if candidate['action'] == 'REVIEW_REQUIRED':
            if candidate['indices'][0] in invalid_linked_component:
                candidate['action'] = 'QUARANTINE_LINKED_INVALID_RECORD'
            elif candidate['indices'][0] in quarantined:
                candidate['action'] = 'QUARANTINE_LINKED_IDENTITY_CONFLICT'

    return {
        'schema': 'storagescope.reconciliation.v1',
        'records': len(records),
        'candidate_count': len(candidates),
        'candidates': candidates,
        'invalid_records': invalid,
        'quarantined_indices': sorted(quarantined),
        'direct_conflict_indices': sorted(direct_conflicts),
        'duplicate_source_indices': sorted(duplicate_source_indices),
        'invalid_identity_origin_indices': sorted(invalid_identity_origin_indices),
        'invalid_identity_link_indices': sorted(invalid_identity_link_indices),
        'propagated_quarantine_indices': sorted(quarantined - direct_conflicts - invalid_identity_link_indices),
        'assessment': ('INCOMPLETE' if invalid or quarantined else
                       'REVIEW_REQUIRED' if candidates else 'NO_CANDIDATES'),
        'automatic_merges': 0,
        'destructive_changes': 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description='Read-only CMDB reconciliation')
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    # Reuse the same bounded, strict parser as the Windows desktop review.
    # Never allow CLI JSON semantics to weaken evidence provenance checks.
    from cmdb_review_desktop_v6198 import review_cmdb_file
    report = review_cmdb_file(args.input)
    content = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if args.output:
        # A review report must never silently overwrite an existing artifact.
        with args.output.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(content)
    else:
        print(content, end='')
    return 2 if report['assessment'] == 'INCOMPLETE' else 0


if __name__ == '__main__':
    raise SystemExit(main())
