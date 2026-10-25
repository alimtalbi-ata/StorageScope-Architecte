# StorageScope V6.230 — Manufacturer-aware CMDB reconciliation

**Author: Abdelhalim Talbi** · 2026-10-25 · Read-only evidence processing.

## Reproduced defect

Two observations with the same serial number but different manufacturers were previously marked `REVIEW_REQUIRED`, even though serial numbers are not globally unique across vendors. A third unlabelled observation linked to the same serial could also remain reviewable. A single record containing contradictory `vendor` and `manufacturer` fields was accepted as match evidence. The V6.230 synthetic regression suite reproduced these defects before the change (nine failed assertions/subtests).

## Correction and risk boundary

`inventory_reconcile_v619.py` now normalizes manufacturer evidence from `manufacturer` and `vendor` using Unicode case-folding and collapsed whitespace, without guessing brand aliases. Missing and explicitly unknown values remain unknown. Invalid field types and contradictory descriptions in one observation invalidate that observation for reconciliation. Two observations with matching serial, WWN, or UUID but different *known* manufacturers are quarantined with `identity_conflicts.field = manufacturer`; connected identity observations inherit quarantine. Different source identifiers remain mandatory for independent evidence. Nothing is auto-merged or written to the CMDB.

This is a conservative identity-integrity gate, not an assertion that manufacturer labels are globally canonical. For example, `Dell`, `Dell EMC` and `Dell Technologies` are not silently conflated: an operator must explicitly reconcile naming conventions. Missing vendor metadata does not imply agreement. Existing quarantine rules for source duplicates, asset kinds and other strong identifiers are retained.

## Verification and evidence

- `python -m unittest discover -s 04-Tests-et-Qualification -p 'test_cmdb_manufacturer_identity_v6230.py' -v`
- `python -m unittest discover -s 04-Tests-et-Qualification -p 'test_cmdb_*v6*.py' -v`
- Windows: `python 04-Tests-et-Qualification/qualify_frozen_cmdb_manufacturer_v6230.py --exe <qualified-StorageScope.exe>` after a real PyInstaller build.
- CI: governance tests on Linux/Windows, native Windows frozen executable, installer and portable gates.

All fixtures are **synthetic**, and there are **no real application screenshots** in this change. A green governance CI is not sufficient to claim Windows qualification; the Windows-native workflow must finish on the exact commit, and published binary SHA-256 values must be independently verified. TOGAF/ISO 42010 architecture evidence and ISO 27001/27040 integrity controls are supported by preserving provenance and explicit human review; this feature alone does not certify compliance.
