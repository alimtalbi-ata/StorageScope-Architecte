"""Optional offline HMAC-SHA256 authentication of SAN/NAS observations.

An operator provisions a different shared key per source through an environment
variable. No key material is stored in snapshots or emitted in reports. HMAC
proves possession of a shared secret, not independent collector identity or
clock correctness. This module makes no network or infrastructure changes.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import hmac
import json
import os
import re

_SOURCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")
_KEY_ID = re.compile(r"[A-Z][A-Z0-9_]{0,31}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_HEX_KEY = re.compile(r"(?:[0-9a-fA-F]{2}){32,128}\Z")
_DOMAIN = b"StorageScope.observation.hmac-sha256.v1\x00"


def load_auth_policy(topology):
    """Return bounded source-to-key IDs; v2 permits a two-key rotation window."""
    enforcement = os.environ.get('STORAGESCOPE_REQUIRE_OBSERVATION_AUTH', '0')
    require_v2 = os.environ.get('STORAGESCOPE_REQUIRE_OBSERVATION_AUTH_V2', '0')
    if enforcement not in ('0', '1'):
        raise ValueError('Invalid observation authentication enforcement setting')
    # Validate operator switches before branching on payload presence. Otherwise
    # an invalid V2 value was silently accepted when a policy happened to exist.
    if require_v2 not in ('0', '1'):
        raise ValueError('Invalid observation authentication v2 enforcement setting')
    if 'observation_auth_policy' not in topology:
        if enforcement == '1' or require_v2 == '1':
            raise ValueError('Observation authentication policy required by operator')
        return None
    raw = topology['observation_auth_policy']
    if require_v2 not in ('0', '1'):
        raise ValueError('Invalid observation authentication v2 enforcement setting')
    if (not isinstance(raw, dict) or set(raw) != {'schema', 'source_keys'} or
            raw.get('schema') not in ('storagescope.observation-auth-policy.v1',
                                      'storagescope.observation-auth-policy.v2')):
        raise ValueError('Invalid observation_auth_policy schema or fields')
    version = raw['schema'].rsplit('.', 1)[-1]
    if require_v2 == '1' and version != 'v2':
        raise ValueError('Operator requires observation authentication policy v2')
    keys = raw['source_keys']
    if not isinstance(keys, dict) or not 1 <= len(keys) <= 64:
        raise ValueError('source_keys must contain 1 to 64 sources')
    all_ids = []
    for source, configured in keys.items():
        if not isinstance(source, str) or not _SOURCE.fullmatch(source):
            raise ValueError('Invalid authentication source reference')
        if version == 'v1':
            if not isinstance(configured, str) or not _KEY_ID.fullmatch(configured):
                raise ValueError('Invalid v1 source key ID')
            all_ids.append(configured)
        else:
            if (not isinstance(configured, list) or not 1 <= len(configured) <= 2 or
                    any(not isinstance(item, str) or not _KEY_ID.fullmatch(item)
                        for item in configured)):
                raise ValueError('v2 source keys must contain one or two valid key IDs')
            all_ids.extend(configured)
    if len(all_ids) != len(set(all_ids)):
        raise ValueError('Key IDs must be unique across all sources and rotation slots')
    return (dict(keys) if version == 'v1' else
            {source: tuple(ids) for source, ids in keys.items()})


def _canonical_payload(record):
    """Stable UTF-8 serialization excluding only the authentication envelope."""
    payload = {key: value for key, value in record.items() if key != 'auth'}
    return _DOMAIN + json.dumps(payload, sort_keys=True, separators=(',', ':'),
                                ensure_ascii=False, allow_nan=False).encode('utf-8')


def sign_observation(record, key_id, secret):
    """Sign a copy of an observation in an offline collector; never modify input."""
    if (not isinstance(record, dict) or not isinstance(key_id, str) or
            not _KEY_ID.fullmatch(key_id) or not isinstance(secret, bytes) or
            not 32 <= len(secret) <= 128):
        raise ValueError('Invalid observation, key ID or HMAC key length')
    result = dict(record)
    result.pop('auth', None)
    result['auth'] = {'key_id': key_id,
                      'hmac_sha256': hmac.new(secret, _canonical_payload(result),
                                             hashlib.sha256).hexdigest()}
    return result


def classify_auth(record, policy, environ=None):
    """Return VERIFIED or a bounded failure category, never a key or source ID."""
    if policy is None:
        return 'NOT_ASSESSED'
    if not isinstance(record, dict):
        return 'INVALID_PAYLOAD'
    source = record.get('source_ref')
    if not isinstance(source, str) or not _SOURCE.fullmatch(source):
        return 'MISSING_SOURCE'
    permitted = policy.get(source)
    if permitted is None:
        return 'UNKNOWN_SOURCE'
    permitted_ids = (permitted,) if isinstance(permitted, str) else permitted
    auth = record.get('auth')
    if auth is None:
        return 'MISSING_AUTH'
    if (not isinstance(auth, dict) or set(auth) != {'key_id', 'hmac_sha256'} or
            auth.get('key_id') not in permitted_ids or
            not isinstance(auth.get('hmac_sha256'), str) or
            not _DIGEST.fullmatch(auth['hmac_sha256'])):
        return 'INVALID_AUTH'
    if environ is None:
        environ = os.environ
    secret_hex = environ.get('STORAGESCOPE_HMAC_KEY_' + auth['key_id'])
    if not isinstance(secret_hex, str) or not _HEX_KEY.fullmatch(secret_hex):
        return 'KEY_UNAVAILABLE'
    try:
        expected = hmac.new(bytes.fromhex(secret_hex), _canonical_payload(record),
                            hashlib.sha256).hexdigest()
    except (TypeError, ValueError, OverflowError, RecursionError):
        return 'INVALID_PAYLOAD'
    return 'VERIFIED' if hmac.compare_digest(expected, auth['hmac_sha256']) else 'BAD_SIGNATURE'


def summarize_auth(paths, shares, policy, environ=None):
    """Count results without exposing collector IDs, signatures or secrets."""
    if policy is None:
        return None
    counts = Counter(classify_auth(item, policy, environ) for item in (*paths, *shares))
    return {'schema': 'storagescope.observation-auth-result.v1',
            'verified_observations': counts['VERIFIED'],
            'missing_source_observations': counts['MISSING_SOURCE'],
            'unknown_source_observations': counts['UNKNOWN_SOURCE'],
            'missing_auth_observations': counts['MISSING_AUTH'],
            'invalid_auth_observations': counts['INVALID_AUTH'],
            'key_unavailable_observations': counts['KEY_UNAVAILABLE'],
            'bad_signature_observations': counts['BAD_SIGNATURE'],
            'invalid_payload_observations': counts['INVALID_PAYLOAD'],
            'authentication': 'SHARED_KEY_HMAC_VERIFIED_ONLY',
            'rotation_active_sources': sum(isinstance(ids, tuple) and len(ids) == 2
                                           for ids in policy.values()),
            'scope_note': 'HMAC verifies shared-key possession and payload integrity; no independent collector identity, trusted time or replay prevention'}


def find_replayed_observations(paths, shares, policy, environ=None):
    """Quarantine all copies of repeated verified HMAC envelopes in one snapshot.

    This is NOT cross-snapshot replay protection; no persistent ledger or
    trusted clock exists. Order-independent, read-only and secret-free.
    """
    if policy is None:
        return set(), set()
    seen, duplicates = {}, set()
    for kind, records in (('paths', paths), ('shares', shares)):
        for index, record in enumerate(records):
            if classify_auth(record, policy, environ) != 'VERIFIED':
                continue
            auth = record['auth']
            signature = (record['source_ref'], auth['key_id'], auth['hmac_sha256'])
            identity = (kind, index)
            if signature in seen:
                duplicates.add(identity)
                duplicates.add(seen[signature])
            else:
                seen[signature] = identity
    return ({i for kind, i in duplicates if kind == 'paths'},
            {i for kind, i in duplicates if kind == 'shares'})
