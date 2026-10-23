"""Bounded, fail-closed CMDB reconciliation review for the Windows desktop.

Reads one local snapshot and produces a review-only report; never writes to CMDB.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import json
from pathlib import Path

from inventory_reconcile_v619 import reconcile

MAX_INPUT_BYTES = 8 * 1024 * 1024


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON property: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"Non-finite JSON value rejected: {value}")


def review_cmdb_file(source):
    """Parse a bounded UTF-8 JSON array, preserving provenance and conflicts."""
    source = Path(source)
    if not source.is_file():
        raise ValueError('CMDB snapshot does not exist')
    with source.open('rb') as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if not raw or len(raw) > MAX_INPUT_BYTES:
        raise ValueError('CMDB snapshot is empty or exceeds the 8 MiB limit')
    try:
        records = json.loads(raw.decode('utf-8-sig'),
                             object_pairs_hook=_unique_object,
                             parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(f'Invalid UTF-8 CMDB JSON: {exc}') from exc
    return reconcile(records)


def format_cmdb_report(report, limit=100):
    """Show summary and bounded candidates, never hide quarantines or invalids."""
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError('Invalid CMDB display limit')
    lines = [f"Évaluation CMDB : {report['assessment']}",
             f"Enregistrements : {report['records']}",
             f"Candidats à revue : {report['candidate_count']}",
             f"Enregistrements invalides : {len(report['invalid_records'])}",
             f"Indices en quarantaine : {len(report['quarantined_indices'])}",
             'Lecture seule · Aucune fusion ni modification CMDB automatique', '']
    quarantined = report['quarantined_indices']
    if quarantined:
        lines.append(f"Indices en quarantaine (maximum {limit} affichés) : "
                     + ', '.join(str(index) for index in quarantined[:limit]))
        if len(quarantined) > limit:
            lines.append(f"… {len(quarantined) - limit} indices en quarantaine supplémentaires non affichés")
    for invalid in report['invalid_records'][:limit]:
        lines.append(f"[INVALIDE] index={invalid['index']} motif={invalid['reason']}")
    if len(report['invalid_records']) > limit:
        lines.append(f"… {len(report['invalid_records']) - limit} invalides supplémentaires non affichés")
    for candidate in report['candidates'][:limit]:
        lines.append(f"[{candidate['action']}] indices={candidate['indices']} "
                     f"preuves={candidate['identity_evidence']}")
        for conflict in candidate['identity_conflicts']:
            lines.append(f"  Identité contradictoire : {conflict['field']}")
        lines.append('  Revue humaine obligatoire · aucune fusion automatique')
    if len(report['candidates']) > limit:
        lines.append(f"… {len(report['candidates']) - limit} candidats supplémentaires non affichés")
    return '\n'.join(lines)


def export_cmdb_report(source, destination):
    """Create one JSON evidence report exclusively; refuse overwrites."""
    report = review_cmdb_file(source)
    payload = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    with Path(destination).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(payload)
    return report
