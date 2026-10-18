"""Severity-filtered, read-only alert navigation. Author: Abdelhalim Talbi."""
from campaign_kpi_v531 import comparison_kpis, evidence_for_point

SEVERITIES = ('critical', 'warning', 'info')

def alert_view(history, first_id, second_id, *, severity='all', **filters):
    if severity not in (*SEVERITIES, 'all'):
        raise ValueError('invalid alert severity')
    kpis = comparison_kpis(history, first_id, second_id, **filters)
    alerts = [dict(a) for a in kpis['alerts'] if severity == 'all' or a['severity'] == severity]
    for alert in alerts:
        code = alert['code']
        if code == 'paired_degradation':
            ids = [p['id'] for p in kpis['points'] if p['delta'] is not None and p['delta'] < 0]
        elif code == 'unmatched_evidence':
            ids = [p['id'] for p in kpis['points'] if p['delta'] is None]
        elif code == 'route_mismatch':
            ids = [p['id'] for p in kpis['points'] if p.get('second_evidence') and p['second_evidence'].get('routes_equal') is False]
        elif code == 'sample_regression':
            ids = [p['id'] for p in kpis['points'] if p.get('second_gain') is not None and p['second_gain'] < -.10]
        else:
            ids = []
        alert['evidence_ids'] = ids
        alert['evidence_coverage'] = 'partial' if len(ids) < alert['count'] else 'complete'
    return {'alerts':alerts,'severity':severity,'kpis':kpis,'overall_gate':kpis['overall_gate'],
            'recommendation_only':True,'production_activation':False,'filter_is_descriptive_only':True}

def alert_evidence(view, code, point_id):
    if not isinstance(view,dict) or not isinstance(code,str):
        raise ValueError('invalid alert view')
    matches = [a for a in view['alerts'] if a['code'] == code]
    if len(matches) != 1 or point_id not in matches[0]['evidence_ids']:
        raise ValueError('evidence not linked to alert')
    return evidence_for_point(view['kpis'], point_id)
