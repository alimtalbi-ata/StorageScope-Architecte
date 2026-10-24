# StorageScope V6.200 — SAN path evidence quarantine

**Author:** Abdelhalim Talbi  
**Date:** 2026-10-23  
**Product internal version:** 6.108 (unchanged). V6.200 identifies this engineering cycle.

## Verified defect / root cause

The v6.199 risk engine stored only the latest state for each physical
`(host_id, storage_id, fabric, port)` signature. A sequence `up, down, up`
was able to reset the previous `unknown` conflict marker to `up`, reporting
a verified active SAN path even though the evidence was contradictory. The
dependency engine already retained conflicting valid states, causing the two
reports to disagree. Invalid path states were previously skipped by dependency
mapping and could therefore leave another `up` observation looking verified.

**Impact:** potentially misleading resilience, blast-radius and host-array
dependency evidence; no observed production incident is claimed.

## Corrected algorithm

```text
Bounded topology JSON -> risk engine -> dependency evidence -> Diagnostic / frozen CLI
                             |                    |
                       physical signature    same signature
                             |                    |
                clean, unique valid state -> observed
                conflicting states        -> sticky quarantine
                invalid state + valid     -> sticky quarantine
                unrelated independent     -> preserved, but assessment incomplete
```

The risk engine now maintains an explicit conflict set and invalid-state
signature set. Neither later records nor input ordering can restore a
quarantined physical path to verified status. Conflicts increment invalid
evidence count, forcing `assessment=INCOMPLETE`. Invalid telemetry on
otherwise trusted endpoints also quarantines that signature. Invalid-only
signatures are not counted as validated paths.

The dependency mapper retains invalid state observations as untrusted evidence
instead of discarding them, and never certifies the affected signature.
Independent, uncontradicted fabrics remain observed; a host-array pair with
one healthy independent fabric is **not** proof of SAN redundancy.

## Contract / security

- Schemas remain `storagescope.storage-risk.v1` and
  `storagescope.storage-dependencies.v1`; no automatic CMDB changes.
- `up/down/up` for one physical signature: zero verified active paths,
  one unverified host-array relationship, `INCOMPLETE` assessment.
- `up/bogus` or `bogus/up`: same fail-closed behavior.
- Two clean independent fabrics: two verified active paths and one observed
  host-array relationship.
- No network discovery, privileged operation, secret or destructive change.
- `CONFLICTING_PATH_STATE` is emitted once per conflicted signature.
- Existing JSON export remains exclusive (never overwrites evidence).

## Regression and native Windows gates

```bash
python -m unittest discover -s 04-Tests-et-Qualification -p 'test_storage_path_quarantine_v6200.py' -v
python -m unittest discover -s 04-Tests-et-Qualification -p 'test_storage_path_risk_v6194.py' -v
python -m unittest discover -s 04-Tests-et-Qualification -p 'test_storage_dependency_impact_v6199.py' -v
```

Governance CI executes the new suite on Linux and Windows. Native Windows CI
runs the frozen `StorageScope.exe --storage-risk-file` against a synthetic
`up/down/up` fixture before the existing historical, PyInstaller, Inno Setup,
install/uninstall, portable and SHA-256 release gates. No test is disabled.
A successful governance CI alone is **not** Windows qualification.

**Evidence status:** source changes and tests are real; until the exact-head
GitHub CI completes, do not claim the new native Windows build is qualified.
No real GUI screenshot, vendor collector or manual UX test is included.

## Architecture alignment

- **ISO/IEC/IEEE 42010 / TOGAF:** explicit evidence-scoped infrastructure view.
- **ArchiMate:** observed technology dependencies, no inferred application service.
- **ITIL 4:** conservative configuration/incident impact analysis.
- **ISO 27001 / ISO 27040:** evidence integrity and fail-closed SAN assessment.

## Next engineering priorities

1. Vendor-specific offline import adapters (NetApp, Dell, Pure) with explicit
   provenance and capture timestamp, without inventing live collector evidence.
2. Bounded identity reconciliation and storage-service dependency joins.
3. Real GUI screenshots and human Windows UX qualification, clearly separated
   from automated smoke tests.
