"""Operator-managed, HMAC-authenticated replay-ledger checkpoint (V6.225).

An anchor is a separate, immutable checkpoint: the operator MUST store it in a
separately protected location, outside the ledger backup/restore domain.
Neither this module nor SQLite can prevent restoring BOTH files together.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime
import hashlib
import hmac
import json
import os
from pathlib import Path
import uuid

from storage_replay_ledger_v6222 import _open_existing

_SCHEMA = 'storagescope.replay-anchor.v1'
_ENV_KEY = 'STORAGESCOPE_REPLAY_ANCHOR_KEY'
_MAX_ANCHOR_BYTES = 4096


def _key():
    raw = os.environ.get(_ENV_KEY, '')
    if len(raw) != 64:
        raise ValueError('Replay anchor requires a 32-byte hexadecimal operator key')
    try:
        return bytes.fromhex(raw)
    except ValueError as exc:
        raise ValueError('Replay anchor requires a hexadecimal operator key') from exc


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(',', ':'), allow_nan=False).encode('ascii')


def _checkpoint(ledger_path, secret):
    # A read transaction pins one consistent SQLite snapshot for the audit/MAC.
    with closing(_open_existing(ledger_path, read_only=True)) as db:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        mac = hmac.new(secret, b'StorageScope replay ledger anchor V6.225\x00', hashlib.sha256)
        count = 0
        for source, collection_id, observations, stamp in db.execute(
                'SELECT source_ref, collection_id, observation_count, accepted_utc '
                'FROM collection_seen ORDER BY source_ref, collection_id'):
            if not isinstance(source, str) or not source.strip():
                raise ValueError('Replay ledger contains invalid collection metadata')
            try:
                parsed_id = uuid.UUID(collection_id) if isinstance(collection_id, str) else None
            except (ValueError, AttributeError):
                parsed_id = None
            if (parsed_id is None or parsed_id.version != 4 or str(parsed_id) != collection_id or
                    type(observations) is not int or observations <= 0):
                raise ValueError('Replay ledger contains invalid collection metadata')
            try:
                dt = datetime.fromisoformat(stamp) if isinstance(stamp, str) else None
            except (TypeError, ValueError):
                dt = None
            if (dt is None or dt.tzinfo is None or dt.utcoffset() is None or
                    dt.utcoffset().total_seconds() != 0):
                raise ValueError('Replay ledger contains invalid UTC timestamp')
            row = _canonical([source, collection_id, observations, stamp])
            mac.update(len(row).to_bytes(8, 'big'))
            mac.update(row)
            count += 1
        mac.update(b'END\x00')
        mac.update(count.to_bytes(8, 'big'))
        return {'schema': _SCHEMA, 'registered_collections': count,
                'ledger_mac_sha256': mac.hexdigest()}


def _anchor_path(ledger_path, anchor_path):
    ledger = Path(ledger_path)
    anchor = Path(anchor_path)
    if anchor.is_symlink() or anchor.parent.is_symlink():
        raise ValueError('Replay anchor must not use a symlink')
    if not anchor.parent.is_dir():
        raise ValueError('Replay anchor parent directory is missing')
    if anchor.parent.resolve() == ledger.parent.resolve():
        raise ValueError('Replay anchor must be stored outside ledger directory')
    return anchor


def create_anchor(ledger_path, anchor_path):
    """Create a NEW anchor exclusively; never overwrite an older checkpoint."""
    anchor = _anchor_path(ledger_path, anchor_path)
    checkpoint = _checkpoint(ledger_path, _key())
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, 'O_NOFOLLOW'):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(anchor, flags, 0o600)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(_canonical(checkpoint) + b'\n')
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        anchor.unlink(missing_ok=True)
        raise
    return {'schema': _SCHEMA, 'status': 'ANCHOR_CREATED',
            'registered_collections': checkpoint['registered_collections'],
            'automatic_changes': 0,
            'scope_note': 'Protect anchor independently; no automatic ledger changes'}


def verify_anchor(ledger_path, anchor_path):
    """Fail closed on a missing, modified or outdated checkpoint; read only."""
    anchor = _anchor_path(ledger_path, anchor_path)
    if not anchor.is_file():
        raise ValueError('Replay anchor missing')
    with anchor.open('rb') as input_file:
        raw = input_file.read(_MAX_ANCHOR_BYTES + 1)
    if len(raw) > _MAX_ANCHOR_BYTES:
        raise ValueError('Replay anchor invalid')
    try:
        expected = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise ValueError('Replay anchor invalid') from exc
    if (not isinstance(expected, dict) or
            set(expected) != {'schema', 'registered_collections', 'ledger_mac_sha256'} or
            expected['schema'] != _SCHEMA or
            type(expected['registered_collections']) is not int or
            expected['registered_collections'] < 0 or
            not isinstance(expected['ledger_mac_sha256'], str) or
            len(expected['ledger_mac_sha256']) != 64):
        raise ValueError('Replay anchor invalid')
    current = _checkpoint(ledger_path, _key())
    if (expected['registered_collections'] != current['registered_collections'] or
            not hmac.compare_digest(expected['ledger_mac_sha256'], current['ledger_mac_sha256'])):
        raise ValueError('REPLAY_LEDGER_ROLLBACK_OR_TAMPERING: anchor mismatch')
    return {'schema': _SCHEMA, 'status': 'VERIFIED', 'integrity': 'PASS',
            'registered_collections': current['registered_collections'],
            'automatic_changes': 0,
            'scope_note': 'Checkpoint verification only; co-restore of ledger and anchor cannot be detected'}
