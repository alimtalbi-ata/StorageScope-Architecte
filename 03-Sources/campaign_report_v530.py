"""Read-only auditable comparison exports. Author: Abdelhalim Talbi."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from campaign_visual_v529 import overlay_data


def comparison_report(history, first_id, second_id, **filters):
    result = overlay_data(history, first_id, second_id, **filters)
    summary = result['summary']
    return {'schema': 'storagescope.campaign-comparison.v5.30', 'campaigns': [
        {'id': result['first_id'], 'sha256': result['first_sha256']},
        {'id': result['second_id'], 'sha256': result['second_sha256']}],
        'filters': result['filters'], 'summary': summary,
        'matched_count': result['matched_count'], 'unmatched_count': result['unmatched_count'],
        'evidence': result['points'], 'overall_gate': result['overall_gate'],
        'recommendation_only': True, 'production_activation': False,
        'note': 'Filtered data is descriptive; no production activation.'}


def _atomic_write(destination, content):
    target = Path(destination)
    if not target.parent.is_dir():
        raise ValueError('destination directory does not exist')
    name = None
    try:
        with NamedTemporaryFile('w', encoding='utf-8', newline='', dir=target.parent,
                                prefix='.ss530-', delete=False) as f:
            name = f.name
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, target)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def export_report(history, first_id, second_id, destination, *, format='json', **filters):
    report = comparison_report(history, first_id, second_id, **filters)
    if format == 'json':
        content = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    elif format == 'csv':
        stream = io.StringIO(newline='')
        writer = csv.writer(stream)
        writer.writerow(['measure_id', 'gain_a', 'gain_b', 'delta_b_minus_a', 'baseline_a_seconds',
                         'candidate_a_seconds', 'baseline_b_seconds', 'candidate_b_seconds',
                         'routes_equal_a', 'routes_equal_b'])
        for p in report['evidence']:
            a, b = p['first_evidence'], p['second_evidence']
            writer.writerow([p['id'], p['first_gain'], p['second_gain'], p['delta'],
                             a['baseline_seconds'] if a else '', a['candidate_seconds'] if a else '',
                             b['baseline_seconds'] if b else '', b['candidate_seconds'] if b else '',
                             a['routes_equal'] if a else '', b['routes_equal'] if b else ''])
        content = stream.getvalue()
    elif format == 'md':
        def fmt(x): return '—' if x is None else f'{x:+.2%}'
        lines = ['# StorageScope v5.30 — Comparaison des campagnes', '',
                 'Auteur : Abdelhalim Talbi', '',
                 f"Campagne A : `{first_id}` — SHA-256 `{report['campaigns'][0]['sha256']}`",
                 f"Campagne B : `{second_id}` — SHA-256 `{report['campaigns'][1]['sha256']}`", '',
                 f"Mesures appariées : {report['matched_count']} ; non appariées : {report['unmatched_count']}",
                 f"Écart des gains médians : {fmt(report['summary']['delta_median_gain'])}", '',
                 '| Mesure | Gain A | Gain B | Écart B−A |', '|---|---:|---:|---:|']
        for p in report['evidence']:
            ident = str(p['id']).replace('|', '\\|').replace('\n', ' ')
            lines.append(f"| {ident} | {fmt(p['first_gain'])} | {fmt(p['second_gain'])} | {fmt(p['delta'])} |")
        lines += ['', '**Consultatif uniquement.** Filtres descriptifs ; aucune activation de production.', '']
        content = '\n'.join(lines)
    else:
        raise ValueError('unsupported export format')
    _atomic_write(destination, content)
    return {'path': str(destination), 'format': format,
            'sha256': hashlib.sha256(content.encode('utf-8')).hexdigest(),
            'matched_count': report['matched_count']}
