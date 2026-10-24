"""Bounded, read-only SAN/NAS topology review for the Windows desktop.

No discovery, CMDB mutation, network access or automatic remediation.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import json
from pathlib import Path

from storage_path_risk_v6194 import assess
from storage_dependency_impact_v6199 import map_dependencies

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


def assess_topology_file(source):
    """Read one bounded UTF-8 JSON snapshot and return explainable risk evidence."""
    source = Path(source)
    if not source.is_file():
        raise ValueError("Topology file does not exist")
    with source.open('rb') as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if not raw or len(raw) > MAX_INPUT_BYTES:
        raise ValueError("Topology file is empty or exceeds the 8 MiB limit")
    try:
        topology = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_unique_object,
                              parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(f"Invalid UTF-8 topology JSON: {exc}") from exc
    report = assess(topology)
    report['dependency_impact'] = map_dependencies(topology, report)
    return report


def format_risk_report(report, limit=200):
    """Text projection for the Tk diagnostics panel; never hide incompleteness."""
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("Invalid finding display limit")
    findings = report['findings']
    lines = [f"Évaluation : {report['assessment']}",
             f"Équipements fiables : {report['assets']}",
             f"Chemins actifs vérifiés : {report['verified_active_paths']}",
             f"Enregistrements invalides : {report['invalid_records']}",
             f"Constats : {report['finding_count']}",
             "Mode lecture seule · Aucune modification CMDB ni remédiation automatique", ""]
    for finding in findings[:limit]:
        lines.append(f"[{finding['level']}] {finding['code']} — {finding['object_id']}")
        lines.append(f"  Preuve : {finding['evidence']}")
        lines.append(f"  Action proposée : {finding['recommended_action']}")
    if len(findings) > limit:
        lines.append(f"… {len(findings) - limit} constats supplémentaires non affichés")
    impact = report.get('dependency_impact')
    if impact:
        lines.extend(['', f"Dépendances observées : {impact['assessment']}",
                      f"Relations hôtes vérifiées : {impact['verified_host_relationships']}",
                      f"Relations hôtes non vérifiées : {impact['unverified_host_relationships']}",
                      f"Relations hôtes à preuves mixtes : {impact.get('mixed_evidence_host_relationships', 0)}",
                      f"Partages NAS vérifiés : {impact['verified_share_relationships']}",
                      'Portée : chemins hôte-baie et partages NAS uniquement, sans impact applicatif présumé'])
        for asset in impact['assets'][:limit]:
            lines.append(f"[{asset['scope']}] {asset['asset_id']} ({asset['kind']}) "
                         f"hôtes={asset['verified_host_ids']} "
                         f"non_vérifiés={asset['unverified_host_ids']} "
                         f"preuves_mixtes={asset.get('mixed_evidence_host_ids', [])} "
                         f"partages={asset['verified_share_ids']}")
        if len(impact['assets']) > limit:
            lines.append(f"… {len(impact['assets']) - limit} équipements supplémentaires non affichés")
    return '\n'.join(lines)


def export_risk_report(source, destination):
    """Write a new JSON report exclusively, never overwrite an existing file."""
    report = assess_topology_file(source)
    payload = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    destination = Path(destination)
    # Exclusive creation prevents overwriting existing evidence. Clean only
    # the file created by this call if write/flush/close fails.
    stream = destination.open('x', encoding='utf-8', newline='\n')
    try:
        with stream:
            stream.write(payload)
            stream.flush()
    except BaseException:
        try:
            destination.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return report
