"""Read-only, vendor-neutral SAN/NAS capacity and resilience assessment.

Input schema: storagescope.storage-topology.v1. No auto-remediation or CMDB writes.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from storage_observation_time_v6215 import parse_observed_at
from storage_observation_freshness_v6216 import load_policy, classify_observation
from storage_source_policy_v6218 import load_source_policy, classify_source, summarize_sources
from storage_observation_auth_v6219 import load_auth_policy, classify_auth, summarize_auth, find_replayed_observations

LEVELS = ("CRITICAL", "HIGH", "MEDIUM", "INFO")
VALID_KINDS = {"host", "storage_array", "nas", "san_switch"}
ACTIVE_STATES = {"up", "active"}
KNOWN_STATES = ACTIVE_STATES | {"down", "disabled", "unknown"}


def _identifier(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def _number(value):
    # bool is an int in Python, but is not a meaningful capacity value.
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value < float("inf")


def assess(topology, warning_percent=85, critical_percent=95):
    """Return deterministic findings; incomplete topology is never marked healthy.

    Each finding includes the affected object, evidence and an actionable next step.
    This function never mutates topology or performs network operations.
    """
    if not isinstance(topology, dict):
        raise ValueError("Topology must be an object")
    if topology.get("schema") != "storagescope.storage-topology.v1":
        raise ValueError("Unsupported topology schema")
    if not (0 < warning_percent < critical_percent <= 100):
        raise ValueError("Capacity thresholds must satisfy 0 < warning < critical <= 100")
    for name in ("assets", "paths", "shares"):
        if not isinstance(topology.get(name), list):
            raise ValueError(f"{name} must be an array")

    policy = load_policy(topology)
    source_policy = load_source_policy(topology)
    auth_policy = load_auth_policy(topology)
    replayed_paths, replayed_shares = find_replayed_observations(
        topology['paths'], topology['shares'], auth_policy)
    findings = []
    assets = {}
    hosts = set()
    storage = set()
    paths_by_pair = defaultdict(list)
    path_states = {}
    # Once a physical signature is contradicted, later records cannot make it healthy.
    conflicted_signatures = set()
    invalid_state_signatures = set()
    invalid_count = 0
    # Quarantine repeated IDs regardless of kind or record ordering, including
    # malformed duplicate records that could otherwise escape reconciliation.
    asset_id_counts = Counter(_identifier(item.get("id")) for item in topology["assets"]
                              if isinstance(item, dict) and _identifier(item.get("id")))
    quarantined_assets = {ident for ident, count in asset_id_counts.items() if count > 1}

    def emit(level, code, object_id, evidence, action):
        findings.append({"level": level, "code": code, "object_id": object_id,
                         "evidence": evidence, "recommended_action": action})

    for ident in sorted(quarantined_assets):
        invalid_count += 1
        emit("HIGH", "DUPLICATE_ASSET", ident,
             f"{asset_id_counts[ident]} records with the same asset ID",
             "Reconcile all records for this ID before using the asset")

    for i, item in enumerate(topology["assets"]):
        if not isinstance(item, dict):
            invalid_count += 1
            emit("HIGH", "INVALID_ASSET", f"assets[{i}]", "Expected object", "Correct source inventory")
            continue
        ident = _identifier(item.get("id"))
        if ident in quarantined_assets:
            continue  # All conflicting copies, even malformed ones, are untrusted.
        kind = item.get("kind")
        if not ident or not isinstance(kind, str) or kind not in VALID_KINDS:
            invalid_count += 1
            emit("HIGH", "INVALID_ASSET", f"assets[{i}]", "Missing id or unsupported kind", "Correct asset identity and kind")
            continue
        assets[ident] = item
        if kind == "host":
            hosts.add(ident)
        if kind in {"storage_array", "nas"}:
            storage.add(ident)

    # Only assess trusted identities. Capacity on a quarantined asset must not
    # be reported as if the first of several contradictory records were valid.
    for ident, item in sorted(assets.items()):
        if item["kind"] in {"storage_array", "nas"}:
            used, total = item.get("used_gib"), item.get("total_gib")
            if used is None or total is None:
                emit("MEDIUM", "CAPACITY_UNASSESSED", ident, "Missing used_gib or total_gib", "Collect both capacity metrics")
            elif not _number(used) or not _number(total) or total == 0 or used > total:
                invalid_count += 1
                emit("HIGH", "INVALID_CAPACITY", ident, "Capacity must be finite, nonnegative and used <= total > 0", "Correct source metrics")
            else:
                # Classify against the unrounded ratio: 94.9999% is not 95%.
                pct = used / total * 100
                if pct >= critical_percent:
                    emit("CRITICAL", "CAPACITY_CRITICAL", ident, f"{pct}% used", "Plan immediate capacity remediation")
                elif pct >= warning_percent:
                    emit("HIGH", "CAPACITY_WARNING", ident, f"{pct}% used", "Review forecast and expansion")

    for i, item in enumerate(topology["paths"]):
        if not isinstance(item, dict):
            invalid_count += 1
            emit("HIGH", "INVALID_PATH", f"paths[{i}]", "Expected object", "Correct path inventory")
            continue
        host = _identifier(item.get("host_id"))
        target = _identifier(item.get("storage_id"))
        fabric = _identifier(item.get("fabric"))
        state = item.get("state")
        # Invalid states on otherwise trusted endpoints poison the same physical
        # signature in either input order. Do not keep an earlier healthy sample.
        endpoints_valid = (host and target and fabric and host in hosts
                           and target in storage and assets[target]["kind"] == "storage_array")
        signature = (host, target, fabric, _identifier(item.get("port")))
        if i in replayed_paths:
            invalid_count += 1
            emit('HIGH', 'REPLAYED_PATH_OBSERVATION', f'paths[{i}]',
                 'Repeated verified HMAC envelope within this snapshot',
                 'Recollect independently; investigate duplicate collector output')
            if endpoints_valid:
                invalid_state_signatures.add(signature)
                path_states[signature] = 'unknown'
            continue
        if auth_policy is not None and classify_auth(item, auth_policy) != 'VERIFIED':
            invalid_count += 1
            emit('HIGH', 'UNAUTHENTICATED_PATH_OBSERVATION', f'paths[{i}]',
                 'Missing, invalid or unverifiable observation HMAC',
                 'Recollect signed evidence and provision the approved collector key securely')
            if endpoints_valid:
                invalid_state_signatures.add(signature)
                path_states[signature] = 'unknown'
            continue
        if source_policy is not None and classify_source(item, source_policy) != 'ALLOWED':
            invalid_count += 1
            emit('HIGH', 'UNTRUSTED_PATH_SOURCE', f'paths[{i}]',
                 'Source missing, invalid or absent from explicit allowlist',
                 'Recollect with an operator-approved source_ref; verify source independently')
            if endpoints_valid:
                invalid_state_signatures.add(signature)
                path_states[signature] = 'unknown'
            continue
        if parse_observed_at(item)[0] == "INVALID":
            invalid_count += 1
            emit("HIGH", "INVALID_PATH_TIMESTAMP", f"paths[{i}]",
                 "observed_at must be a timezone-aware ISO 8601 timestamp",
                 "Recollect path evidence with an authenticated observation time")
            if endpoints_valid:
                invalid_state_signatures.add(signature)
                path_states[signature] = "unknown"
            continue
        freshness = classify_observation(item, policy)
        if policy is not None and freshness != 'FRESH':
            invalid_count += 1
            emit('HIGH', 'PATH_' + freshness + '_OBSERVATION', f'paths[{i}]',
                 'Observation is not fresh under explicit policy reference time',
                 'Recollect path telemetry and verify reference clock and source')
            if endpoints_valid:
                invalid_state_signatures.add(signature)
                path_states[signature] = 'unknown'
            continue
        if not host or not target or not fabric or not isinstance(state, str) or state not in KNOWN_STATES:
            invalid_count += 1
            emit("HIGH", "INVALID_PATH", f"paths[{i}]", "Missing endpoint/fabric or invalid state", "Correct path evidence")
            if endpoints_valid:
                invalid_state_signatures.add(signature)
                if signature in path_states:
                    path_states[signature] = "unknown"
            continue
        if not endpoints_valid:
            invalid_count += 1
            emit("HIGH", "ORPHAN_PATH", f"paths[{i}]", f"Unresolved host/array: {host} -> {target}", "Reconcile endpoints")
            continue
        # Two records on one fabric do not constitute two independent fabrics.
        if signature in invalid_state_signatures:
            path_states[signature] = "unknown"
            continue
        if signature in conflicted_signatures:
            continue  # Sticky quarantine, even after up/down/up observations.
        if signature in path_states:
            if path_states[signature] != state:
                emit("HIGH", "CONFLICTING_PATH_STATE", f"paths[{i}]", "Conflicting states for one endpoint/fabric/port", "Reconcile timestamped path telemetry")
                invalid_count += 1
                conflicted_signatures.add(signature)
                path_states[signature] = "unknown"
            else:
                emit("MEDIUM", "DUPLICATE_PATH_EVIDENCE", f"paths[{i}]", "Repeated endpoint/fabric/port", "Deduplicate discovery evidence")
            continue
        path_states[signature] = state

    for (host, target, fabric, _port), state in path_states.items():
        paths_by_pair[(host, target)].append((fabric, state))

    for host, target in sorted(paths_by_pair):
        observations = paths_by_pair[(host, target)]
        healthy = {fabric for fabric, state in observations if state in ACTIVE_STATES}
        down = sorted({fabric for fabric, state in observations if state in {"down", "disabled"}})
        unknown = sorted({fabric for fabric, state in observations if state == "unknown"})
        pair_id = f"{host}->{target}"
        if not healthy:
            emit("CRITICAL" if not unknown else "HIGH", "NO_VERIFIED_ACTIVE_PATH", pair_id,
                 f"Active fabrics: 0; unknown={unknown}; down={down}", "Verify connectivity and path telemetry")
        elif len(healthy) < 2:
            emit("HIGH", "SINGLE_ACTIVE_FABRIC", pair_id,
                 f"Active fabrics: {sorted(healthy)}; unknown={unknown}; down={down}", "Validate independent SAN fabric connectivity")
        if down:
            emit("HIGH", "PATH_DOWN", pair_id, f"Down/disabled fabrics: {down}", "Investigate fabric and multipath health")
        if unknown:
            emit("MEDIUM", "PATH_STATE_UNKNOWN", pair_id, f"Unknown fabrics: {unknown}", "Collect current path state")

    for host in sorted(hosts):
        if not any(key[0] == host for key in paths_by_pair):
            emit("MEDIUM", "HOST_PATHS_UNASSESSED", host, "No validated host-to-array paths", "Collect SAN paths or mark host as non-SAN")
    for target in sorted(x for x in storage if assets[x]["kind"] == "storage_array"):
        if not any(key[1] == target for key in paths_by_pair):
            emit("MEDIUM", "ARRAY_PATHS_UNASSESSED", target, "No validated host-to-array paths", "Collect host connectivity evidence")

    # A share ID is a unique inventory identity, even across NAS controllers.
    # A duplicate cannot inherit the first record's apparently healthy quota.
    share_id_counts = Counter(_identifier(share.get("id")) for share in topology["shares"]
                              if isinstance(share, dict) and _identifier(share.get("id")))
    duplicate_shares = {ident for ident, count in share_id_counts.items() if count > 1}
    for ident in sorted(duplicate_shares):
        invalid_count += 1
        emit("HIGH", "DUPLICATE_SHARE", ident,
             f"{share_id_counts[ident]} records with the same share ID",
             "Reconcile NAS share identity before evaluating quota")

    for i, share in enumerate(topology["shares"]):
        if not isinstance(share, dict):
            invalid_count += 1
            emit("HIGH", "INVALID_SHARE", f"shares[{i}]", "Expected object", "Correct NAS share record")
            continue
        ident = _identifier(share.get("id"))
        # Duplicate share identity and verified replay are independent findings.
        # Report each replayed copy before the duplicate-ID quarantine so audit
        # evidence is not hidden, while never assessing its quota as trusted.
        if i in replayed_shares:
            invalid_count += 1
            emit('HIGH', 'REPLAYED_SHARE_OBSERVATION', f'shares[{i}]',
                 'Repeated verified HMAC envelope within this snapshot',
                 'Recollect independently; investigate duplicate collector output')
            continue
        if ident in duplicate_shares:
            continue  # All conflicting copies are quarantined.
        if auth_policy is not None and classify_auth(share, auth_policy) != 'VERIFIED':
            invalid_count += 1
            emit('HIGH', 'UNAUTHENTICATED_SHARE_OBSERVATION', f'shares[{i}]',
                 'Missing, invalid or unverifiable observation HMAC',
                 'Recollect signed evidence and provision the approved collector key securely')
            continue
        if source_policy is not None and classify_source(share, source_policy) != 'ALLOWED':
            invalid_count += 1
            emit('HIGH', 'UNTRUSTED_SHARE_SOURCE', f'shares[{i}]',
                 'Source missing, invalid or absent from explicit allowlist',
                 'Recollect with an operator-approved source_ref; verify source independently')
            continue
        if parse_observed_at(share)[0] == "INVALID":
            invalid_count += 1
            emit("HIGH", "INVALID_SHARE_TIMESTAMP", f"shares[{i}]",
                 "observed_at must be a timezone-aware ISO 8601 timestamp",
                 "Recollect share evidence with an authenticated observation time")
            continue
        freshness = classify_observation(share, policy)
        if policy is not None and freshness != 'FRESH':
            invalid_count += 1
            emit('HIGH', 'SHARE_' + freshness + '_OBSERVATION', f'shares[{i}]',
                 'Observation is not fresh under explicit policy reference time',
                 'Recollect NAS share evidence and verify reference clock and source')
            continue
        target = _identifier(share.get("nas_id"))
        protocol = share.get("protocol")
        if not ident or target not in assets or assets[target]["kind"] != "nas" or not isinstance(protocol, str) or protocol not in {"NFS", "SMB"}:
            invalid_count += 1
            emit("HIGH", "INVALID_SHARE", f"shares[{i}]", "Missing share/NAS or unsupported protocol", "Reconcile NAS share and protocol")
            continue
        used, quota = share.get("used_gib"), share.get("quota_gib")
        if used is None or quota is None:
            emit("MEDIUM", "SHARE_QUOTA_UNASSESSED", ident, "Missing used_gib or quota_gib", "Collect share quota metrics")
        elif not _number(used) or not _number(quota) or quota == 0 or used > quota:
            invalid_count += 1
            emit("HIGH", "INVALID_SHARE_QUOTA", ident, "Invalid share capacity or quota", "Correct share metrics")
        else:
            # Never round a quota into a higher severity band.
            pct = used / quota * 100
            if pct >= critical_percent:
                emit("CRITICAL", "SHARE_QUOTA_CRITICAL", ident, f"{pct}% quota used", "Review NAS quota and growth")
            elif pct >= warning_percent:
                emit("HIGH", "SHARE_QUOTA_WARNING", ident, f"{pct}% quota used", "Review NAS quota forecast")

    if not topology["assets"] and not topology["paths"] and not topology["shares"]:
        emit("MEDIUM", "TOPOLOGY_EMPTY", "topology", "No inventory or path evidence",
             "Collect a bounded inventory before assessing infrastructure health")

    findings.sort(key=lambda f: (LEVELS.index(f["level"]), f["code"], f["object_id"], f["evidence"]))
    return {"schema": "storagescope.storage-risk.v1", "assets": len(assets),
            "validated_paths": sum(map(len, paths_by_pair.values())),
            "verified_active_paths": sum(state in ACTIVE_STATES for state in path_states.values()),
            "quarantined_asset_ids": sorted(quarantined_assets),
            "quarantined_share_ids": sorted(duplicate_shares),
            "source_evaluation": summarize_sources(topology['paths'], topology['shares'], source_policy),
            "observation_authentication": summarize_auth(topology['paths'], topology['shares'], auth_policy),
            "replayed_path_observations": len(replayed_paths),
            "replayed_share_observations": len(replayed_shares),
            "invalid_records": invalid_count, "counts": dict(sorted(Counter(f["level"] for f in findings).items())),
            "findings": findings, "finding_count": len(findings), "automatic_changes": 0,
            "assessment": "INCOMPLETE" if invalid_count or any(f["code"] == "TOPOLOGY_EMPTY" or f["code"].endswith("UNASSESSED") for f in findings)
            else ("RISKS_FOUND" if findings else "NO_FINDINGS_IN_ASSESSED_SCOPE")}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only SAN/NAS resilience and capacity assessment")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = assess(json.loads(args.input.read_text(encoding="utf-8")))
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 2 if report["invalid_records"] else (1 if report["finding_count"] else 0)


if __name__ == "__main__":
    raise SystemExit(main())
