"""Read-only evidence comparison for StorageScope benchmark campaigns.
Author: Abdelhalim Talbi.
"""
import json
from pathlib import Path
from statistics import median


def compare_campaigns(history, first_id, second_id, *, nodes=None, edits=None, spacing=None, limit=10000):
    if not isinstance(first_id, str) or not isinstance(second_id, str) or not first_id or not second_id or first_id == second_id:
        raise ValueError('select two distinct campaign ids')
    from campaign_dashboard_v527 import dashboard_data
    # Validate filters through the same public API; never change the unfiltered safety gate.
    overview = dashboard_data(history, nodes=nodes, edits=edits, spacing=spacing, limit=limit)
    records = {r['id']: r for r in history.list(limit)}
    if first_id not in records or second_id not in records:
        raise ValueError('campaign not found in history')
    selected = []
    for cid in (first_id, second_id):
        r = records[cid]
        pairs = [p for p in r['campaign']['pairs'] if (nodes is None or p['nodes'] == nodes)
                 and (edits is None or p['edits'] == edits)
                 and (spacing is None or p['spacing'] == spacing)]
        if not pairs:
            selected.append({'id': cid, 'sha256': r['sha256'], 'sample_count': 0, 'median_gain': None,
                             'regressions': 0, 'mismatches': 0, 'evidence': []})
            continue
        gains = [(p['baseline_seconds']-p['candidate_seconds'])/p['baseline_seconds'] for p in pairs]
        selected.append({'id': cid, 'sha256': r['sha256'], 'sample_count': len(pairs),
                         'median_gain': median(gains), 'regressions': sum(g < -.10 for g in gains),
                         'mismatches': sum(p['routes_equal'] is not True for p in pairs),
                         'evidence': [{'id': p['id'], 'baseline_seconds': p['baseline_seconds'],
                                       'candidate_seconds': p['candidate_seconds'], 'routes_equal': p['routes_equal'],
                                       'gain': g} for p, g in zip(pairs, gains)]})
    delta = (selected[1]['median_gain'] - selected[0]['median_gain']
             if all(c['median_gain'] is not None for c in selected) else None)
    return {'campaigns': selected, 'delta_median_gain': delta, 'filters': overview['filters'],
            'overall_gate': overview['overall_gate'], 'recommendation_only': True,
            'production_activation': False, 'filter_is_descriptive_only': True}


def export_comparison(history, first_id, second_id, destination, **filters):
    result = compare_campaigns(history, first_id, second_id, **filters)
    Path(destination).write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
    return result
