"""Explicit, deterministic SAN/NAS observation-age policy (no system clock).

The reference instant is caller supplied and never authenticated by this module.
Legacy snapshots without a policy retain the V6.215 behavior.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime

from storage_observation_time_v6215 import parse_observed_at


def load_policy(topology):
    """Return normalized policy or None; reject malformed policies fail-closed."""
    if 'freshness_policy' not in topology:
        return None
    raw = topology['freshness_policy']
    if not isinstance(raw, dict) or raw.get('schema') != 'storagescope.observation-freshness-policy.v1':
        raise ValueError('Unsupported freshness policy schema')
    if set(raw) - {'schema', 'reference_time', 'max_age_seconds', 'max_future_skew_seconds'}:
        raise ValueError('Unknown freshness policy field')
    status, reference = parse_observed_at({'observed_at': raw.get('reference_time')})
    if status != 'VALID':
        raise ValueError('freshness_policy.reference_time must be timezone-aware ISO 8601')
    age = raw.get('max_age_seconds')
    skew = raw.get('max_future_skew_seconds', 0)
    if type(age) is not int or not 1 <= age <= 31_536_000:
        raise ValueError('freshness_policy.max_age_seconds must be 1..31536000 integer')
    if type(skew) is not int or not 0 <= skew <= 3600:
        raise ValueError('freshness_policy.max_future_skew_seconds must be 0..3600 integer')
    return {'schema': raw['schema'], 'reference_time': reference,
            'max_age_seconds': age, 'max_future_skew_seconds': skew}


def classify_observation(observation, policy):
    """FRESH|STALE|FUTURE|MISSING|INVALID; FRESH is not authenticated."""
    status, instant = parse_observed_at(observation)
    if status != 'VALID':
        return status
    if policy is None:
        return 'NOT_ASSESSED'
    reference = datetime.fromisoformat(policy['reference_time'].replace('Z', '+00:00'))
    observed = datetime.fromisoformat(instant.replace('Z', '+00:00'))
    delta = (reference - observed).total_seconds()
    if delta < -policy['max_future_skew_seconds']:
        return 'FUTURE'
    if delta > policy['max_age_seconds']:
        return 'STALE'
    return 'FRESH'


def summarize_freshness(paths, shares, policy):
    """A deterministic, bounded count of policy assessments, not a trust claim."""
    if policy is None:
        return None
    counts = Counter(classify_observation(item, policy) for item in (*paths, *shares))
    return {'schema': 'storagescope.observation-freshness-result.v1',
            'reference_time': policy['reference_time'],
            'max_age_seconds': policy['max_age_seconds'],
            'max_future_skew_seconds': policy['max_future_skew_seconds'],
            'fresh_observations': counts['FRESH'],
            'stale_observations': counts['STALE'],
            'future_observations': counts['FUTURE'],
            'missing_observations': counts['MISSING'],
            'invalid_observations': counts['INVALID'],
            'trust': 'UNAUTHENTICATED_INPUT_CLOCK',
            'scope_note': 'Explicit reference time only; neither timestamp nor collection source authenticated'}
