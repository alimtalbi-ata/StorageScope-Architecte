"""Read-only, vendor-neutral SAN/NAS capacity and resilience assessment.

Input schema: storagescope.storage-topology.v1. No auto-remediation or CMDB writes.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

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

    findings = []
    assets = {}
    hosts = set()
    storage = set()
    paths_by_pair = defaultdict(list)
    path_states = {}
    invalid_count = 0

    def emit(level, code, object_id, evidence, action):
        findings.append({"level": level, "code": code, "object_id": object_id,
                         "evidence": evidence, "recommended_action": action})

    for i, item in enumerate(topology["assets"]):
        if not isinstance(item, dict):
            invalid_count += 1
            emit("HIGH", "INVALID_ASSET", f"assets[{i}]", "Expected object", "Correct source inventory")
            continue
        ident = _identifier(item.get("id"))
        kind = item.get("kind")
        if not ident or not isinstance(kind, str) or kind not in VALID_KINDS:
            invalid_count += 1
            emit("HIGH", "INVALID_ASSET", f"assets[{i}]", "Missing id or unsupported kind", "Correct asset identity and kind")
            continue
        if ident in assets:
            invalid_count += 1
            emit("HIGH", "DUPLICATE_ASSET", ident, f"Duplicate at assets[{i}]", "Reconcile duplicate asset IDs")
            continue
        assets[ident] = item
        if kind == "host":
            hosts.add(ident)
        if kind in {"storage_array", "nas"}:
            storage.add(ident)
        if kind in {"storage_array", "nas"}:
            used, total = item.get("used_gib"), item.get("total_gib")
            if used is None or total is None:
                emit("MEDIUM", "CAPACITY_UNASSESSED", ident, "Missing used_gib or total_gib", "Collect both capacity metrics")
            elif not _number(used) or not _number(total) or total == 0 or used > total:
                invalid_count += 1
                emit("HIGH", "INVALID_CAPACITY", ident, "Capacity must be finite, nonnegative and used <= total > 0", "Correct source metrics")
            else:
                pct = round(used / total * 100, 2)
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
        if not host or not target or not fabric or not isinstance(state, str) or state not in KNOWN_STATES:
            invalid_count += 1
            emit("HIGH", "INVALID_PATH", f"paths[{i}]", "Missing endpoint/fabric or invalid state", "Correct path evidence")
            continue
        if host not in hosts or target not in storage or assets[target]["kind"] != "storage_array":
            invalid_count += 1
            emit("HIGH", "ORPHAN_PATH", f"paths[{i}]", f"Unresolved host/array: {host} -> {target}", "Reconcile endpoints")
            continue
        # Two records on one fabric do not constitute two independent fabrics.
        signature = (host, target, fabric, _identifier(item.get("port")))
        if signature in path_states:
            if path_states[signature] != state:
                emit("HIGH", "CONFLICTING_PATH_STATE", f"paths[{i}]", "Conflicting states for one endpoint/fabric/port", "Reconcile timestamped path telemetry")
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

    for i, share in enumerate(topology["shares"]):
        if not isinstance(share, dict):
            invalid_count += 1
            emit("HIGH", "INVALID_SHARE", f"shares[{i}]", "Expected object", "Correct NAS share record")
            continue
        ident = _identifier(share.get("id"))
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
            pct = round(used / quota * 100, 2)
            if pct >= critical_percent:
                emit("CRITICAL", "SHARE_QUOTA_CRITICAL", ident, f"{pct}% quota used", "Review NAS quota and growth")
            elif pct >= warning_percent:
                emit("HIGH", "SHARE_QUOTA_WARNING", ident, f"{pct}% quota used", "Review NAS quota forecast")

    findings.sort(key=lambda f: (LEVELS.index(f["level"]), f["code"], f["object_id"], f["evidence"]))
    return {"schema": "storagescope.storage-risk.v1", "assets": len(assets),
            "validated_paths": sum(map(len, paths_by_pair.values())),
            "invalid_records": invalid_count, "counts": dict(sorted(Counter(f["level"] for f in findings).items())),
            "findings": findings, "finding_count": len(findings), "automatic_changes": 0,
            "assessment": "INCOMPLETE" if invalid_count or any(f["code"].endswith("UNASSESSED") for f in findings)
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
