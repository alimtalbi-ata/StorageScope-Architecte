"""Read-only, fail-closed KPI and evidence navigation model. Author: Abdelhalim Talbi."""
from campaign_visual_v529 import overlay_data


def comparison_kpis(history, first_id, second_id, **filters):
    view = overlay_data(history, first_id, second_id, **filters)
    s = view['summary']
    points = view['points']
    improved = sum(p['delta'] is not None and p['delta'] > 0 for p in points)
    degraded = sum(p['delta'] is not None and p['delta'] < 0 for p in points)
    unchanged = view['matched_count'] - improved - degraded
    alerts = []
    if s['second_mismatches']:
        alerts.append({'severity':'critical','code':'route_mismatch','count':s['second_mismatches']})
    if s['second_regressions']:
        alerts.append({'severity':'warning','code':'sample_regression','count':s['second_regressions']})
    if degraded:
        alerts.append({'severity':'warning','code':'paired_degradation','count':degraded})
    if view['unmatched_count']:
        alerts.append({'severity':'info','code':'unmatched_evidence','count':view['unmatched_count']})
    return {'first_id':first_id,'second_id':second_id,'matched':view['matched_count'],
            'unmatched':view['unmatched_count'],'improved':improved,'degraded':degraded,
            'unchanged':unchanged,'median_delta':s['delta_median_gain'],
            'alerts':alerts,'points':points,'sha256':(view['first_sha256'],view['second_sha256']),
            'overall_gate':view['overall_gate'],'recommendation_only':True,
            'production_activation':False,'filter_is_descriptive_only':True}


def evidence_for_point(kpis, point_id):
    if not isinstance(point_id,str) or not point_id:
        raise ValueError('invalid evidence id')
    for point in kpis['points']:
        if point['id'] == point_id:
            return {'id':point_id,'first':point['first_evidence'],
                    'second':point['second_evidence'], 'delta':point['delta'],
                    'campaign_sha256':kpis['sha256'], 'recommendation_only':True,
                    'production_activation':False}
    raise ValueError('evidence not found')
