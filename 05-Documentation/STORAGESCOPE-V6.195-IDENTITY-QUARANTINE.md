# StorageScope V6.195 — SAN/NAS identity quarantine and coverage gate

**Author: Abdelhalim Talbi — 23 October 2026**

## Purpose and risk addressed

V6.194 introduced a read-only SAN/NAS path, capacity and quota assessor. A duplicate asset ID was reported, but the first record remained trusted. A contradictory array identity could therefore supply apparently valid capacity evidence, and two SAN fabrics attached to a duplicated host could still appear verified. Repeated NAS share IDs were also not rejected. An entirely empty topology returned `NO_FINDINGS_IN_ASSESSED_SCOPE`, which could be misinterpreted as health.

V6.195 applies a **fail-closed identity quarantine** before capacity and connectivity assessment. It does not edit CMDB records, change zoning, connect to equipment or execute remediation.

## Changed contracts

- Asset IDs are normalized by stripping surrounding whitespace. Any ID occurring more than once in `assets` is quarantined **regardless of record order or validity of the duplicate kind**. The report contains `DUPLICATE_ASSET` and `quarantined_asset_ids`. All records for that ID are excluded from trusted assets, hosts and arrays.
- A SAN path referencing a quarantined endpoint becomes `ORPHAN_PATH` rather than a verified path. Capacity is assessed only after duplicate detection, so the first contradictory record cannot provide false capacity confidence.
- Any share ID repeated across `shares` is quarantined regardless of NAS or protocol. `DUPLICATE_SHARE` and `quarantined_share_ids` explain the reconciliation requirement. No quota conclusion is drawn from conflicting records.
- Empty input arrays now yield `TOPOLOGY_EMPTY` and `assessment=INCOMPLETE`. A lack of evidence is not a green status.
- The report adds `verified_active_paths`. The existing `validated_paths` field is retained for compatibility: it counts syntactically valid path observations, including down/unknown paths. **It must not be used as an availability KPI.**
- Existing severity and exit-code contracts remain: 0 for no findings, 1 for findings, 2 for invalid evidence. All changes remain read-only and deterministic.

## Reproduction and verification

From the repository root:

```powershell
py -3 -m unittest discover -s "04-Tests-et-Qualification" -p "test_storage_path_risk_v6194.py" -v
py -3 "03-Sources/storage_path_risk_v6194.py" topology.json --output risk-report.json
```

The test suite contains 24 tests: the 18 pre-existing V6.194 tests, one strengthened duplicate-asset expectation and six new scenarios (host identity conflict, malformed duplicate identity, array conflict in both orders, share ID collision, unique-share quota preserved, active-path counting). Local Linux qualification on 23 October 2026: **24/24 PASS**. This is **not** a native Windows build or UI qualification. GitHub Windows/Linux CI evidence must be checked on the new PR head before claiming cross-platform success.

## Risk model and standards

- **ISO/IEC/IEEE 42010 / TOGAF:** explicit identity assumptions, scope and quality gates before architecture risk decisions.
- **ArchiMate:** quarantined technology nodes and paths must not be depicted as verified dependencies.
- **ITIL 4:** reconcile conflicting inventory records via controlled review before change approval or incident remediation.
- **ISO 27001 / ISO 27040:** integrity and traceability of storage evidence, without asserting compliance certification.

## Remaining limitations and release gates

No vendor-specific collectors, timestamp freshness, multipath ALUA/ANA interpretation, service-level dependency graph, CMDB writeback, UX integration or UI screenshots are provided. The V6.195 change is in Python sources and tests; previously qualified Windows binaries do not contain it. A green governance CI is insufficient: full Windows PyInstaller/Inno Setup, installation/uninstallation, portable and SHA-256 evidence must be independently verified at the exact release commit. Never merge automatically.
