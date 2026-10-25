# StorageScope V6.231 — Strict CMDB strong-identity type validation

**Author: Abdelhalim Talbi** · 2026-10-25 · Read-only evidence.

## Reproduced defect and root cause

`inventory_reconcile_v619._identity` historically returned `None` for any non-string value. A record with `serial="S1"` and `wwn=123` silently discarded the malformed WWN, while the serial matched another observation. This yielded `REVIEW_REQUIRED` instead of an invalid observation. The new tests reproduced 21 failed assertions/subtests before the correction. This is a real reconciliation logic defect, not a Windows fixture or compilation error.

## Correction

Before identity matching, every explicitly supplied non-null `serial`, `wwn` and `uuid` must be a string. Numeric, boolean, array and object values invalidate the entire observation with `invalid_identity_type:<field>`, even if another strong field matches. Missing, null, empty and known placeholder strings remain unknown. Existing source, manufacturer, asset-kind, duplicate-source, connected-component quarantine and SHA-256 provenance controls remain enabled. No automatic merge or CMDB write.

## Qualification

Run `python -m unittest discover -s 04-Tests-et-Qualification -p 'test_cmdb_identity_types_v6231.py' -v` and the existing CMDB/inventory suites. The native Windows workflow runs `qualify_frozen_cmdb_identity_types_v6231.py` against a real PyInstaller executable, then the historical tests, Inno Setup, installer/uninstall, portable and SHA-256 gates. Do not claim Windows qualified until those steps complete on the exact commit.

## Limits

All evidence is synthetic. No physical SAN/NAS or CMDB write tests, screenshots, or human UX qualification. This supports traceable architecture evidence (ISO 42010), ITIL 4 configuration integrity, and ISO 27001/27040 integrity objectives, but is not standards certification. Future work: explicitly quarantine valid records linked to invalid identity observations.
