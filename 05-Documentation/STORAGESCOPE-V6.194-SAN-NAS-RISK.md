# StorageScope v6.194 — SAN/NAS risk assessment (read-only)

**Auteur : Abdelhalim Talbi — 23 octobre 2026**

## Objective and scope

This incremental, vendor-neutral engine assesses independent SAN fabrics, host/array path telemetry, storage capacity and NAS share quotas. It complements `inventory_quality_v618.py` and `inventory_reconcile_v619.py`; it does **not** change the CMDB, merge CIs, query vendors, change zoning, or remediate a host. Intended for architecture review, operations triage and evidence-based risk reporting.

## Contract

Input UTF-8 JSON (schema `storagescope.storage-topology.v1`) has three **required arrays**: `assets`, `paths`, `shares`.

- Assets: `id` (unique string), `kind` (`host`, `storage_array`, `nas`, `san_switch`); storage arrays and NAS can provide `used_gib` and `total_gib`.
- SAN paths: `host_id`, `storage_id`, `fabric` (independent failure domain identifier), `state` (`up`, `active`, `down`, `disabled`, `unknown`), optional `port`.
- NAS shares: `id`, `nas_id`, `protocol` (`NFS` or `SMB`), `used_gib`, `quota_gib`.

**Synthetic example (not a real infrastructure capture):**

```json
{
  "schema": "storagescope.storage-topology.v1",
  "assets": [
    {"id": "host-01", "kind": "host"},
    {"id": "array-01", "kind": "storage_array", "used_gib": 920, "total_gib": 1000},
    {"id": "nas-01", "kind": "nas", "used_gib": 200, "total_gib": 1000}
  ],
  "paths": [
    {"host_id": "host-01", "storage_id": "array-01", "fabric": "A", "state": "up"},
    {"host_id": "host-01", "storage_id": "array-01", "fabric": "B", "state": "down"}
  ],
  "shares": [
    {"id": "share-01", "nas_id": "nas-01", "protocol": "SMB", "used_gib": 97, "quota_gib": 100}
  ]
}
```

Run from the repository root:

```powershell
py -3 "03-Sources/storage_path_risk_v6194.py" topology.json --output risk-report.json
py -3 -m unittest discover -s "04-Tests-et-Qualification" -p "test_storage_path_risk_v6194.py" -v
```

Exit codes: **0** = no findings in assessed scope; **1** = findings requiring review; **2** = invalid evidence. Invalid schema raises an error and returns nonzero. Outputs include severity, object ID, specific evidence, recommended action, counts, and `automatic_changes: 0`.

## Detection and qualification principles

- Two active ports on **one** fabric do not count as independent paths. Redundancy requires two distinct active fabric IDs. Duplicate endpoint/fabric/port evidence is reported and ignored for counting.
- `unknown` is not considered active. Missing host/array paths or missing capacity/quota metrics generate **UNASSESSED** findings; incomplete input cannot be reported as healthy.
- Default warning/critical capacity thresholds: **85% / 95%**. Negative, non-finite, boolean, zero total, and overcommitted values are rejected as invalid evidence.
- An orphan path, duplicate asset ID, invalid protocol or malformed record generates a finding; no silent corrections are applied.
- Assessment is deterministic and non-destructive. Source provenance beyond IDs, sampling freshness, multipath policy (ALUA/ANA), SRLG, SAN zoning, HBA port independence, oversubscription and NAS HA are **not** inferred. A no-findings result is **not** a certification of end-to-end resilience.
- The current module is a standalone CLI and library; it is not yet connected to the graphical UI or the PyInstaller import closure. No screenshots are available.

## Standards mapping

- **ISO 42010 / TOGAF:** documented viewpoints, assumptions and architectural evidence for infrastructure review.
- **ArchiMate:** hosts, arrays and SAN fabrics may be mapped to technology nodes and paths; this tool does not create ArchiMate diagrams.
- **ITIL 4:** risk findings support incident, problem and change review, not automatic ticket creation.
- **ISO 27001 / ISO 27040:** traceable assessment of availability and storage resilience, without claiming compliance certification.

## Evidence

Qualification on 2026-10-23: **17/17 targeted tests PASS locally on Linux and 17/17 PASS in GitHub Actions on both Windows and Linux** (run #39963753364, commit 17e3d695). This targeted CI is not a full Windows native build: PyInstaller, Inno Setup, installation, uninstallation and portable smoke tests have **not** run on V6.194. The previous Windows full qualification applies to parent commit 4e4cf4ab only.

Next iteration: explicit per-vendor collector adapters, freshness/provenance, host-to-service dependencies, SRLG, capacity forecasting, UI review workflow, and portable/installer smoke test on the new commit.
