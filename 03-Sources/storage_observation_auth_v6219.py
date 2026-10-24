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
    """Return a bounded source-to-key-ID map, or None for legacy snapshots."""
    enforcement = os.environ.get('STORAGESCOPE_REQUIRE_OBSERVATION_AUTH', '0')
    if enforcement not in ('0', '1'):
        raise ValueError('Invalid observation authentication enforcement setting')
    if 'observation_auth_policy' not in topology:
        if enforcement == '1':
            raise ValueError('Observation authentication policy required by operator')
        return None
    raw = topology['observation_auth_policy']
    if (not isinstance(raw, dict) or
            set(raw) != {'schema', 'source_keys'} or
            raw.get('schema') != 'storagescope.observation-auth-policy.v1'):
        raise ValueError('Invalid observation_auth_policy schema or fields')
    keys = raw['source_keys']
    if (not isinstance(keys, dict) or not 1 <= len(keys) <= 64 or
            any(not isinstance(source, str) or not _SOURCE.fullmatch(source) or
                not isinstance(key_id, str) or not _KEY_ID.fullmatch(key_id)
                for source, key_id in keys.items()) or
            len(set(keys.values())) != len(keys)):
        raise ValueError('source_keys must map distinct bounded sources to distinct key IDs')
    return dict(keys)


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
    expected_key = policy.get(source)
    if expected_key is None:
        return 'UNKNOWN_SOURCE'
    auth = record.get('auth')
    if auth is None:
        return 'MISSING_AUTH'
    if (not isinstance(auth, dict) or set(auth) != {'key_id', 'hmac_sha256'} or
            auth.get('key_id') != expected_key or
            not isinstance(auth.get('hmac_sha256'), str) or
            not _DIGEST.fullmatch(auth['hmac_sha256'])):
        return 'INVALID_AUTH'
    if environ is None:
        environ = os.environ
    secret_hex = environ.get('STORAGESCOPE_HMAC_KEY_' + expected_key)
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
            'scope_note': 'HMAC verifies shared-key possession and payload integrity; no independent collector identity, trusted time or replay prevention'}
