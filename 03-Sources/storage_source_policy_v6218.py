"""Optional, operator-supplied SAN/NAS observation-source allowlist.

This is provenance *screening*, not cryptographic authentication. No external
network, secrets, CMDB mutation, or inferred trust. Author: Abdelhalim Talbi.
"""
from __future__ import annotations

from collections import Counter
import re

_SOURCE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")


def load_source_policy(topology):
    """Return immutable allowed source IDs, or None for legacy snapshots."""
    if 'source_policy' not in topology:
        return None
    raw = topology['source_policy']
    if (not isinstance(raw, dict) or
            raw.get('schema') != 'storagescope.observation-source-policy.v1' or
            set(raw) != {'schema', 'allowed_source_refs'}):
        raise ValueError('Invalid source_policy schema or fields')
    refs = raw['allowed_source_refs']
    if (not isinstance(refs, list) or not 1 <= len(refs) <= 128 or
            any(not isinstance(ref, str) or not _SOURCE_ID.fullmatch(ref) for ref in refs) or
            len(set(refs)) != len(refs)):
        raise ValueError('source_policy.allowed_source_refs must be unique bounded identifiers')
    return frozenset(refs)


def classify_source(record, policy):
    """ALLOWED|MISSING|INVALID|UNLISTED|NOT_ASSESSED (never AUTHENTICATED)."""
    if policy is None:
        return 'NOT_ASSESSED'
    if not isinstance(record, dict) or 'source_ref' not in record:
        return 'MISSING'
    ref = record['source_ref']
    if not isinstance(ref, str) or not _SOURCE_ID.fullmatch(ref):
        return 'INVALID'
    return 'ALLOWED' if ref in policy else 'UNLISTED'


def summarize_sources(paths, shares, policy):
    """Bounded counters; source names never echoed in findings or reports."""
    if policy is None:
        return None
    counts = Counter(classify_source(record, policy) for record in (*paths, *shares))
    return {
        'schema': 'storagescope.observation-source-result.v1',
        'allowed_observations': counts['ALLOWED'],
        'missing_observations': counts['MISSING'],
        'invalid_observations': counts['INVALID'],
        'unlisted_observations': counts['UNLISTED'],
        'authentication': 'NOT_AUTHENTICATED',
        'scope_note': 'Operator-declared allowlist only; no source identity or payload signature verification',
    }
