# StorageScope V6.235 — Collector provenance normalization and quarantine

**Author:** Abdelhalim Talbi. **Date:** 2026-10-25. **Status:** development cycle; Windows qualification requires a green exact-head native workflow.

## Defect and impact

The read-only CMDB reconciliation engine compared collectors using `strip().casefold()` only. A collector labelled `CMDB` and the same collector labelled `ＣＭＤＢ` (Unicode fullwidth compatibility characters) were treated as independent sources. Invisible format characters, terminal escape sequences, line breaks, and excessively long collector labels could also enter provenance and human-readable evidence. This could falsely suggest independent corroboration of a strong SAN/NAS identity or spoof a report.

## Corrective behavior

A collector key is normalized using Unicode NFKC, whitespace compaction and case folding. Collector names longer than 256 Unicode characters, containing control/format/surrogate characters, or Unicode line/paragraph separators are invalid. The raw source remains in the report as submitted, but it cannot participate in matching when invalid. Strong IDs on invalid observations are used **only to quarantine linked valid observations**, never as positive match evidence. Unrelated reviewable identities remain reviewable. This is a fail-closed identity-provenance policy; legitimate vendor names and accented collector names are accepted.

## Architecture and controls

`JSON snapshot (max 8 MiB)` → `strict UTF-8 parser and SHA-256 of exact bytes` → `record and source validation` → `normalized collector comparison` → `identity graph` → `quarantine / review-only report`.

- ISO 27001/27040: evidence integrity, untrusted input handling and auditable provenance.
- ISO 42010 / ArchiMate: source identity and asset relationships are documented and reviewable.
- ITIL 4: reconciliation does not update a CMDB automatically.
- TOGAF: explicit architecture decision to prioritize false-positive containment over automatic merge.

## Regression and deployment

`PYTHONPATH=03-Sources python -m unittest discover -s 04-Tests-et-Qualification -p 'test_cmdb_collector_provenance_v6235.py' -v`

`PYTHONPATH=03-Sources python -m unittest discover -s 04-Tests-et-Qualification -p 'test_cmdb*.py' -v`

The native Windows workflow builds the frozen executable and runs `qualify_frozen_cmdb_source_v6235.py` with `--exe` against that exact build. It checks the quarantine action, unrelated candidate, unchanged input bytes and SHA-256. Do not mark V6.235 Windows-qualified before PyInstaller, Inno Setup, install/uninstall, portable and artifact checks pass on the **same head SHA**.

## Evidence limitations

The synthetic fixtures are not physical SAN/NAS equipment tests. No human Windows UI walkthrough or real UI screenshot is supplied. Version number of the compiled product remains `6.108` unless the release manifests are updated separately. No secret, automatic CMDB merge, destructive deployment or simulated real screenshot is included.
