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
    unresolved_fabric_pairs = set()
    unresolved_paths_by_array = Counter()
    unresolved_path_observations = 0
    for item in topology['paths']:
        if not isinstance(item, dict):
            unresolved_path_observations += 1
            continue
        host, target, fabric = (_id(item.get(k)) for k in ('host_id', 'storage_id', 'fabric'))
        state = item.get('state')
        if trusted.get(host) != 'host' or trusted.get(target) != 'storage_array':
            # Do not invent a host-array relation. Retain a bounded audit count,
            # attributable to the array only when its identity is trusted.
            unresolved_path_observations += 1
            if trusted.get(target) == 'storage_array':
                unresolved_paths_by_array[target] += 1
            continue
        if not fabric:
            # The host/array is identifiable even when the fabric is not.
            # Preserve this as unverified evidence rather than silently
            # discarding it when another path for the pair is healthy.
            unresolved_fabric_pairs.add((host, target))
            continue
        # Keep invalid states as an explicit untrusted observation. Skipping them
        # would let an earlier/later "up" on the same signature look verified.
        observed_state = state if isinstance(state, str) and state in KNOWN else '<invalid>'
        signatures[(host, target, fabric, _id(item.get('port')))].add(observed_state)

    verified_pairs, uncertain_pairs = set(), set(unresolved_fabric_pairs)
    for (host, target, _fabric, _port), states in signatures.items():
        pair = (host, target)
        if len(states) == 1 and next(iter(states)) in ACTIVE:
            verified_pairs.add(pair)
        else:
            uncertain_pairs.add(pair)
    # A healthy alternate fabric must not erase conflicting/unknown evidence
    # on another path for the same host-array pair. Counts are evidence
    # categories, not disjoint populations of hosts.
    mixed_pairs = verified_pairs & uncertain_pairs

    share_counts = Counter(_id(s.get('id')) for s in topology['shares']
                           if isinstance(s, dict) and _id(s.get('id')))
    shares = defaultdict(set)
    unresolved_shares_by_nas = Counter()
    unresolved_share_observations = 0
    for item in topology['shares']:
        if not isinstance(item, dict):
            unresolved_share_observations += 1
            continue
        ident, target = _id(item.get('id')), _id(item.get('nas_id'))
        if (ident and share_counts[ident] == 1 and trusted.get(target) == 'nas'
                and item.get('protocol') in ('NFS', 'SMB')):
            shares[target].add(ident)
        else:
            # Retain ambiguous share evidence even when another share is healthy.
            # Attribute only to uniquely trusted NAS identities.
            unresolved_share_observations += 1
            if trusted.get(target) == 'nas':
                unresolved_shares_by_nas[target] += 1

    hosts_by_array, unverified_by_array = defaultdict(set), defaultdict(set)
    for host, target in verified_pairs:
        hosts_by_array[target].add(host)
    for host, target in uncertain_pairs:
        unverified_by_array[target].add(host)

    results = []
    for ident, kind in sorted(trusted.items()):
        if kind not in STORAGE_KINDS:
            continue
        host_ids = sorted(hosts_by_array.get(ident, set()))
        unverified = sorted(unverified_by_array.get(ident, set()))
        mixed = sorted(hosts_by_array.get(ident, set()) & unverified_by_array.get(ident, set()))
        share_ids = sorted(shares.get(ident, set()))
        results.append({'asset_id': ident, 'kind': kind,
                        'verified_host_ids': host_ids,
                        'unverified_host_ids': unverified,
                        'mixed_evidence_host_ids': mixed,
                        'unresolved_path_observations': unresolved_paths_by_array[ident],
                        'unresolved_share_observations': unresolved_shares_by_nas[ident],
                        'verified_share_ids': share_ids,
                        'scope': 'OBSERVED' if host_ids or share_ids else 'UNASSESSED'})

    incomplete = (risk_report.get('assessment') == 'INCOMPLETE'
                  or bool(uncertain_pairs)
                  or bool(unresolved_path_observations)
                  or bool(unresolved_share_observations)
                  or any(a['scope'] == 'UNASSESSED' for a in results)
                  or not results)
    return {
        'schema': 'storagescope.storage-dependencies.v1',
        'assessment': 'INCOMPLETE' if incomplete else 'OBSERVED_DEPENDENCIES_ONLY',
        'assets': results,
        'asset_count': len(results),
        'verified_host_relationships': len(verified_pairs),
        'unverified_host_relationships': len(uncertain_pairs),
        'mixed_evidence_host_relationships': len(mixed_pairs),
        'unresolved_path_observations': unresolved_path_observations,
        'unresolved_share_observations': unresolved_share_observations,
        'verified_share_relationships': sum(len(s) for s in shares.values()),
        'scope_note': 'Observed host-array paths and NAS shares only; not service-level impact or a complete CMDB dependency map',
        'automatic_changes': 0,
    }
