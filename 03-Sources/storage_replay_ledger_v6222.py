"""Opt-in, local SQLite anti-replay gate for signed SAN/NAS collections.

This gate is intentionally separate from read-only risk analysis. The operator
initializes a ledger once, then explicitly registers a signed collection. No
network, collector or CMDB changes occur. A missing ledger is never recreated
silently. SQLite is not tamper-evident: protect and back up the ledger.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import os
import sqlite3
import stat
import uuid

from storage_observation_auth_v6219 import (
    classify_auth, find_replayed_observations, load_auth_policy,
)
from storage_observation_time_v6215 import parse_observed_at
from storage_path_risk_v6194 import assess
from storage_dependency_impact_v6199 import map_dependencies

_SCHEMA = """CREATE TABLE collection_seen (
    source_ref TEXT NOT NULL,
    collection_id TEXT NOT NULL,
    observation_count INTEGER NOT NULL CHECK(observation_count > 0),
    accepted_utc TEXT NOT NULL,
    PRIMARY KEY (source_ref, collection_id)
) WITHOUT ROWID"""


def _path(path):
    target = Path(path)
    if target.is_symlink():
        raise ValueError('Replay ledger must not be a symlink')
    if not target.parent.is_dir():
        raise ValueError('Replay ledger parent directory is missing')
    return target


def initialize_ledger(path):
    """Create a fresh ledger exclusively; never reset an existing ledger."""
    target = _path(path)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    try:
        with closing(sqlite3.connect(str(target), isolation_level=None, timeout=3)) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute(_SCHEMA)
            db.execute('PRAGMA user_version=1')
            db.execute('COMMIT')
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return {'schema': 'storagescope.replay-ledger.v1', 'status': 'INITIALIZED'}


def _open_existing(path, *, read_only=False):
    target = _path(path)
    if not target.is_file() or not stat.S_ISREG(target.stat().st_mode):
        raise ValueError('Replay ledger missing or not a regular file; explicit initialization required')
    db = sqlite3.connect(target.resolve().as_uri() + ('?mode=ro' if read_only else '?mode=rw'), uri=True,
                         isolation_level=None, timeout=3)
    try:
        if db.execute('PRAGMA quick_check').fetchone() != ('ok',):
            raise ValueError('Replay ledger integrity check failed')
        if db.execute('PRAGMA user_version').fetchone() != (1,):
            raise ValueError('Unsupported replay ledger schema version')
        names = db.execute("SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
        if names != [('table', 'collection_seen')]:
            raise ValueError('Unexpected replay ledger objects')
        columns = list(db.execute('PRAGMA table_info(collection_seen)'))
        if ([row[1] for row in columns] !=
                ['source_ref', 'collection_id', 'observation_count', 'accepted_utc'] or
                [row[5] for row in columns] != [1, 2, 0, 0]):
            raise ValueError('Invalid replay ledger primary key')
        schema_sql = db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='collection_seen'"
        ).fetchone()[0]
        if schema_sql != _SCHEMA:
            raise ValueError('Unexpected replay ledger table definition')
    except BaseException:
        db.close()
        raise
    return db



def inspect_ledger(path):
    """Read-only aggregate health view; never consumes collection IDs.

    Exposes only totals and time bounds, not collector identities, signed
    observations or key material. The ledger must already exist and pass the
    same schema/integrity gate as a registration. SQLite mode=ro is mandatory.
    """
    with closing(_open_existing(path, read_only=True)) as db:
        db.execute('PRAGMA query_only=ON')
        row = db.execute(
            'SELECT COUNT(*), COUNT(DISTINCT source_ref), '
            'COALESCE(SUM(observation_count), 0), '
            'MIN(accepted_utc), MAX(accepted_utc) FROM collection_seen'
        ).fetchone()
        count, sources, observations, first, last = row
        # A min/max-only check misses malformed interior rows: SQLite MIN/MAX
        # compares TEXT lexically, not as timestamps. Stream every row with
        # bounded memory; never expose collector or collection identifiers.
        for source, collection_id, observation_count, stamp in db.execute(
                'SELECT source_ref, collection_id, observation_count, '
                'accepted_utc FROM collection_seen'):
            if not isinstance(source, str) or not source.strip():
                raise ValueError('Replay ledger contains invalid collection metadata')
            try:
                parsed_id = uuid.UUID(collection_id) if isinstance(collection_id, str) else None
            except (ValueError, AttributeError):
                parsed_id = None
            if (parsed_id is None or parsed_id.version != 4 or
                    str(parsed_id) != collection_id or
                    type(observation_count) is not int or observation_count <= 0):
                raise ValueError('Replay ledger contains invalid collection metadata')
            try:
                parsed_time = datetime.fromisoformat(stamp) if isinstance(stamp, str) else None
            except (ValueError, TypeError):
                parsed_time = None
            if (parsed_time is None or parsed_time.tzinfo is None or
                    parsed_time.utcoffset() is None or
                    parsed_time.utcoffset().total_seconds() != 0):
                raise ValueError('Replay ledger contains invalid UTC timestamp')
        return {'schema': 'storagescope.replay-ledger-audit.v1',
                'status': 'READ_ONLY', 'integrity': 'PASS',
                'registered_collections': count,
                'distinct_sources': sources,
                'registered_observations': observations,
                'first_accepted_utc': first, 'last_accepted_utc': last,
                'automatic_changes': 0,
                'scope_note': 'Local SQLite audit only; rollback and tampering by local administrator are not detectable'}

def _collection_groups(topology):
    if not isinstance(topology, dict) or topology.get('schema') != 'storagescope.storage-topology.v1':
        raise ValueError('Invalid topology schema')
    policy_raw = topology.get('observation_auth_policy')
    if not isinstance(policy_raw, dict) or policy_raw.get('schema') != 'storagescope.observation-auth-policy.v2':
        raise ValueError('Replay registration requires HMAC authentication policy v2')
    policy = load_auth_policy(topology)
    paths, shares = topology.get('paths'), topology.get('shares')
    if not isinstance(paths, list) or not isinstance(shares, list) or not (paths or shares):
        raise ValueError('Signed path or share observations required')
    replay_paths, replay_shares = find_replayed_observations(paths, shares, policy)
    if replay_paths or replay_shares:
        raise ValueError('Repeated signed observations inside collection')
    groups = Counter()
    source_collections = {}
    for record in (*paths, *shares):
        if classify_auth(record, policy) != 'VERIFIED':
            raise ValueError('Unsigned, invalid or unverifiable observation')
        raw_id = record.get('collection_id')
        try:
            parsed = uuid.UUID(raw_id) if isinstance(raw_id, str) else None
        except (ValueError, AttributeError):
            parsed = None
        if parsed is None or parsed.version != 4 or str(parsed) != raw_id:
            raise ValueError('Signed collection_id must be canonical UUIDv4')
        if parse_observed_at(record)[0] != 'VALID':
            raise ValueError('Signed observation timestamp required')
        source = record['source_ref']
        if source in source_collections and source_collections[source] != raw_id:
            raise ValueError('Multiple collection IDs for one source in snapshot')
        source_collections[source] = raw_id
        groups[(source, raw_id)] += 1
    return groups


def register_snapshot(topology, ledger_path):
    """Atomically consume each source/collection ID once across snapshots.

    Rejected batches never consume an ID. Concurrent writers serialize through
    BEGIN IMMEDIATE and a unique primary key. This is an explicit write action,
    not called by the read-only assessment UI or --storage-risk-file.
    """
    groups = _collection_groups(topology)
    risk = assess(topology)
    dependencies = map_dependencies(topology, risk)
    if risk['assessment'] == 'INCOMPLETE' or dependencies['assessment'] == 'INCOMPLETE':
        raise ValueError('Incomplete topology cannot be registered as trusted evidence')
    with closing(_open_existing(ledger_path)) as db:
        try:
            db.execute('BEGIN IMMEDIATE')
            stamp = datetime.now(timezone.utc).isoformat()
            for (source, collection_id), count in sorted(groups.items()):
                db.execute('INSERT INTO collection_seen VALUES (?, ?, ?, ?)',
                           (source, collection_id, count, stamp))
            db.execute('COMMIT')
        except sqlite3.IntegrityError as exc:
            db.execute('ROLLBACK')
            raise ValueError('REPLAY_DETECTED: signed collection already registered') from exc
        except BaseException:
            if db.in_transaction:
                db.execute('ROLLBACK')
            raise
    return {'schema': 'storagescope.replay-registration.v1',
            'status': 'ACCEPTED', 'registered_collections': len(groups),
            'registered_observations': sum(groups.values()),
            'risk_assessment': risk['assessment'],
            'dependency_assessment': dependencies['assessment'],
            'automatic_changes': 0,
            'scope_note': 'Local SQLite replay gate; no trusted clock, independent collector identity or tamper-evident ledger'}
