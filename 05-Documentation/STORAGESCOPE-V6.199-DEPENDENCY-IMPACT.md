# StorageScope V6.199 — SAN/NAS dependency evidence and export integrity

**Author:** Abdelhalim Talbi  
**Date:** 2026-10-23  
**Product version:** 6.108 (unchanged); V6.199 is the engineering cycle.

## Scope and architecture

The existing `storagescope.storage-topology.v1` inventory is read in **read-only** mode by `storage_risk_desktop_v6196.assess_topology_file`. It first produces `storagescope.storage-risk.v1` findings, then attaches a new `dependency_impact` object with schema `storagescope.storage-dependencies.v1`.

```text
JSON topology (bounded, UTF-8, unique keys)
       | 
       v
SAN/NAS risk engine V6.194 -- invalid IDs / quarantine / path findings
       |
       +--> Dependency impact V6.199
       |      host -> array: observed path states and fabric/port evidence
       |      share -> NAS: trusted unique share ID and valid NFS/SMB
       |      conflict / unknown / missing -> INCOMPLETE, never healthy
       v
Diagnostic UI / frozen --storage-risk-file command
       |
       v
Exclusive JSON export ('x') -> flush/close -> cleanup on partial failure
```

## Output contract

- `assets[]`: one row per trusted storage array/NAS, with `verified_host_ids`, `unverified_host_ids`, `verified_share_ids` and `scope` (OBSERVED or UNASSESSED).
- `verified_host_relationships`: unique host-array pairs with at least one uncontradicted active path signature.
- `unverified_host_relationships`: observed host-array pairs with only down, disabled, unknown or contradictory path signatures.
- `verified_share_relationships`: unique, non-quarantined NFS/SMB share-to-NAS relationships.
- `assessment`: INCOMPLETE when topology/risk evidence is incomplete, any unresolved host pair exists, or a storage asset has no verified dependency evidence. Otherwise OBSERVED_DEPENDENCIES_ONLY.
- `automatic_changes=0`: never changes the CMDB or executes remediation.

**Important:** observed dependency is *not* verified redundancy or application-service impact. A verified host-array relationship with only one active fabric remains a SAN resilience risk. A missing relationship never proves that the asset has no dependents.

## Security and evidence

- Duplicate asset IDs are quarantined; duplicate share IDs cannot create trusted relationships.
- A single fabric/port signature with contradictory states is unverified regardless of input ordering.
- Invalid or orphan endpoints are not mapped as trusted dependencies.
- Export uses exclusive file creation; disk-full/write/flush/close failures remove the new incomplete output. Existing files are never overwritten.
- No remote access, secrets, discovery, automatic merge or destructive operation.

## Qualification

Run on Python 3.12:

```bash
python -m unittest discover -s 04-Tests-et-Qualification -p 'test_storage_dependency_impact_v6199.py' -v
python -m unittest discover -s 04-Tests-et-Qualification -p 'test_storage_path_risk_v6194.py' -v
python -m unittest discover -s 04-Tests-et-Qualification -p 'test_storage_risk_desktop_v6196.py' -v
```

The native Windows workflow additionally verifies that the **frozen executable** exports dependency evidence, then runs historical tests, PyInstaller/Inno Setup, installer/portable and SHA-256 gates. A green governance job alone is insufficient.

## Architecture / operations standards

- **ISO 42010 / TOGAF ADM:** explicitly scoped architecture views, assumptions and provenance.
- **ArchiMate:** observed technology relationships only; no inferred application/business service association.
- **ITIL 4:** supports configuration and incident impact investigation without mutating the CMDB.
- **ISO 27001 / ISO 27040:** evidence integrity, least privilege, conservative handling of SAN path and storage identities.

## Known limitations and roadmap

No vendor-native NetApp, Dell, Pure or FC switch collector; no timestamp freshness scoring, application-level dependency graph, live monitoring or human UX screenshot evidence. Next: add signed collector provenance and bounded CMDB join, then GUI review of application/service impact. All examples are synthetic, not production observations.
