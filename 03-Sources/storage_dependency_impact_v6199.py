"""Fail-closed SAN/NAS dependency and blast-radius evidence (read-only).

Maps only observed host-array paths and NAS-share relationships. Missing or
contradictory observations never imply resilience, safety, or zero impact.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

from collections import Counter, defaultdict

ACTIVE = frozenset({'up', 'active'})
KNOWN = ACTIVE | {'down', 'disabled', 'unknown'}
STORAGE_KINDS = frozenset({'storage_array', 'nas'})


def _id(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def map_dependencies(topology, risk_report):
    """Build deterministic, evidence-scoped dependencies without mutating inputs.

    A path is verified only if its complete endpoint/fabric/port signature has
    one non-conflicting active state. Down/unknown/conflicting paths are kept as
    *unverified*, never silently dropped or promoted to healthy.
    """
    if not isinstance(topology, dict) or not isinstance(risk_report, dict):
        raise ValueError('Topology and risk report must be objects')
    if topology.get('schema') != 'storagescope.storage-topology.v1':
        raise ValueError('Unsupported topology schema')
    if any(not isinstance(topology.get(k), list) for k in ('assets', 'paths', 'shares')):
        raise ValueError('Topology collections must be arrays')
    if risk_report.get('schema') != 'storagescope.storage-risk.v1':
        raise ValueError('Unsupported risk report schema')

    assets = topology['assets']
    counts = Counter(_id(a.get('id')) for a in assets if isinstance(a, dict) and _id(a.get('id')))
    trusted = {}
    for item in assets:
        if not isinstance(item, dict):
            continue
        ident = _id(item.get('id'))
        kind = item.get('kind')
        if ident and counts[ident] == 1 and isinstance(kind, str) and kind in ('host', 'storage_array', 'nas', 'san_switch'):
            trusted[ident] = kind

    # Preserve *all* observations per physical signature. A conflicting state
    # is not repaired by the last record in the input (order independence).
    signatures = defaultdict(set)
    for item in topology['paths']:
        if not isinstance(item, dict):
            continue
        host, target, fabric = (_id(item.get(k)) for k in ('host_id', 'storage_id', 'fabric'))
        state = item.get('state')
        if (not host or not target or not fabric or not isinstance(state, str) or
                state not in KNOWN or trusted.get(host) != 'host' or
                trusted.get(target) != 'storage_array'):
            continue
        signatures[(host, target, fabric, _id(item.get('port')))].add(state)

    verified_pairs, uncertain_pairs = set(), set()
    for (host, target, _fabric, _port), states in signatures.items():
        pair = (host, target)
        if len(states) == 1 and next(iter(states)) in ACTIVE:
            verified_pairs.add(pair)
        else:
            uncertain_pairs.add(pair)
    # A host with another independent verified path has a known relationship;
    # uncertain observations remain visible in the risk findings themselves.
    uncertain_pairs -= verified_pairs

    share_counts = Counter(_id(s.get('id')) for s in topology['shares']
                           if isinstance(s, dict) and _id(s.get('id')))
    shares = defaultdict(set)
    for item in topology['shares']:
        if not isinstance(item, dict):
            continue
        ident, target = _id(item.get('id')), _id(item.get('nas_id'))
        if (ident and share_counts[ident] == 1 and trusted.get(target) == 'nas'
                and item.get('protocol') in ('NFS', 'SMB')):
            shares[target].add(ident)

    results = []
    for ident, kind in sorted(trusted.items()):
        if kind not in STORAGE_KINDS:
            continue
        host_ids = sorted(h for h, target in verified_pairs if target == ident)
        unverified = sorted(h for h, target in uncertain_pairs if target == ident)
        share_ids = sorted(shares.get(ident, set()))
        results.append({'asset_id': ident, 'kind': kind,
                        'verified_host_ids': host_ids,
                        'unverified_host_ids': unverified,
                        'verified_share_ids': share_ids,
                        'scope': 'OBSERVED' if host_ids or share_ids else 'UNASSESSED'})

    incomplete = (risk_report.get('assessment') == 'INCOMPLETE'
                  or bool(uncertain_pairs)
                  or any(a['scope'] == 'UNASSESSED' for a in results)
                  or not results)
    return {
        'schema': 'storagescope.storage-dependencies.v1',
        'assessment': 'INCOMPLETE' if incomplete else 'OBSERVED_DEPENDENCIES_ONLY',
        'assets': results,
        'asset_count': len(results),
        'verified_host_relationships': len(verified_pairs),
        'unverified_host_relationships': len(uncertain_pairs),
        'verified_share_relationships': sum(len(s) for s in shares.values()),
        'scope_note': 'Observed host-array paths and NAS shares only; not service-level impact or a complete CMDB dependency map',
        'automatic_changes': 0,
    }
