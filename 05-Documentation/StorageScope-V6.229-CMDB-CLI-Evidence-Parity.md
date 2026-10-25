# StorageScope V6.229 — CLI/desktop CMDB evidence parity

**Author: Abdelhalim Talbi** · 2026-10-25 · Read-only reconciliation.

## Observed defect and root cause

The historical standalone command `03-Sources/inventory_reconcile_v619.py` parsed input using an unbounded `Path.read_text()` followed by Python's permissive `json.loads()`. In contrast, the desktop CMDB review already used a bounded, strict parser. As reproduced by the new regression suite, the CLI silently accepted duplicate JSON keys, non-finite numbers and files larger than 8 MiB, and rejected valid UTF-8 BOM snapshots. Its output also omitted the exact-byte source digest.

This discrepancy risks an ambiguous review artifact, not an automatic CMDB write: all reconciliation remains read-only.

## Correction

The CLI now delegates snapshot ingestion to `cmdb_review_desktop_v6198.review_cmdb_file` and therefore shares its established validation: UTF-8 BOM support; strict duplicate-property and NaN/Infinity rejection; 8 MiB maximum; exact source SHA-256 and byte count. Existing exclusive output creation (`open('x')`), exit code 2 for incomplete assessments, and no-auto-merge behavior are retained. The `reconcile(records)` in-memory API is unchanged.

### Usage

```bash
python 03-Sources/inventory_reconcile_v619.py /path/snapshot.json --output /path/cmdb-review.json
```

Use a new output path for every review. The CLI refuses to overwrite an existing report. The SHA-256 proves *byte integrity*, not authenticity, source trust, freshness, or authorization. The application does not contact a CMDB or change any inventory.

## Verification gates

- New `test_cmdb_cli_evidence_parity_v6229.py`: BOM+digest, duplicate keys, non-finite numbers, oversize, exclusive export, stdout fail-closed.
- Prior CLI tests and desktop reconciliation suites retained.
- Governance Linux/Windows workflows run the new suite; Windows native build/historical/installer gates remain mandatory for any Windows qualification.
- Fixtures are synthetic. No physical arrays, user-acceptance testing, or real UI screenshots are included.

## Alignment

The deterministic evidence trace supports **ISO/IEC 42010** architecture rationale, **ITIL 4** configuration-data review and **ISO/IEC 27001/27040** integrity controls; this is engineering alignment, not a certification claim.
