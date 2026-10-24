"""Strict, deterministic provenance timestamps for SAN/NAS observations.

A timestamp is an assertion from the input snapshot, not a verified clock.
No network, wall-clock or CMDB access. Author: Abdelhalim Talbi.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import re

# Reject naive dates, non-ISO forms and excessive precision; never guess UTC.
_ISO_OFFSET = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})$"
)


def parse_observed_at(observation):
    """Return (MISSING|VALID|INVALID, normalized_UTC_or_None).

    Missing is allowed for legacy inventories, but cannot establish freshness.
    Explicitly malformed timestamps are untrusted and must quarantine evidence.
    """
    if not isinstance(observation, dict) or 'observed_at' not in observation:
        return 'MISSING', None
    value = observation['observed_at']
    if not isinstance(value, str) or not _ISO_OFFSET.fullmatch(value):
        return 'INVALID', None
    try:
        instant = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if instant.tzinfo is None or instant.utcoffset() is None:
            return 'INVALID', None
        normalized = instant.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
        return 'VALID', normalized
    except (ValueError, OverflowError):
        return 'INVALID', None


def summarize_observation_times(paths, shares):
    """Count every observation; report parsed timestamps without claiming freshness."""
    counts = Counter()
    latest = None
    for record in (*paths, *shares):
        status, utc = parse_observed_at(record)
        counts[status] += 1
        if utc is not None:
            instant = datetime.fromisoformat(utc.replace('Z', '+00:00'))
            if latest is None or instant > latest:
                latest = instant
    return {
        'schema': 'storagescope.observation-time.v1',
        'valid_observations': counts['VALID'],
        'missing_observations': counts['MISSING'],
        'invalid_observations': counts['INVALID'],
        'latest_parsed_utc': (latest.isoformat().replace('+00:00', 'Z')
                              if latest is not None else None),
        'freshness': 'NOT_ASSESSED',
        'scope_note': 'Input timestamps are unverified; no collection time or freshness inferred',
    }
