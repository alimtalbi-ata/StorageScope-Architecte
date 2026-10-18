"""Read-only overlay visualization model and drill-down evidence. Author: Abdelhalim Talbi."""
from campaign_compare_v528 import compare_campaigns


def overlay_data(history, first_id, second_id, **filters):
    comparison = compare_campaigns(history, first_id, second_id, **filters)
    a, b = comparison['campaigns']
    indexed = [{p['id']: p for p in c['evidence']} for c in (a, b)]
    ids = sorted(set(indexed[0]) | set(indexed[1]))
    points = []
    for ident in ids:
        left, right = indexed[0].get(ident), indexed[1].get(ident)
        points.append({'id': ident, 'first_gain': None if left is None else left['gain'],
                       'second_gain': None if right is None else right['gain'],
                       'delta': None if left is None or right is None else right['gain'] - left['gain'],
                       'first_evidence': left, 'second_evidence': right})
    matched = sum(p['delta'] is not None for p in points)
    return {'first_id': first_id, 'second_id': second_id, 'points': points,
            'matched_count': matched, 'unmatched_count': len(points)-matched,
            'first_sha256': a['sha256'], 'second_sha256': b['sha256'],
            'summary': {'first_median_gain': a['median_gain'], 'second_median_gain': b['median_gain'],
                        'delta_median_gain': comparison['delta_median_gain'],
                        'first_regressions': a['regressions'], 'second_regressions': b['regressions'],
                        'first_mismatches': a['mismatches'], 'second_mismatches': b['mismatches']},
            'overall_gate': comparison['overall_gate'], 'filters': comparison['filters'],
            'recommendation_only': True, 'production_activation': False,
            'filter_is_descriptive_only': True}


def draw_overlay(canvas, data, *, width=900, height=220):
    """Render two curves; call only on Tk main thread. Handles empty/single-point datasets."""
    canvas.delete('all')
    points = data['points']
    if not points:
        canvas.create_text(width//2, height//2, text='Aucune mesure correspondante')
        return
    usable = [abs(p[k]) for p in points for k in ('first_gain','second_gain') if p[k] is not None]
    scale = max([.05] + usable)
    left, right, top, bottom = 55, width-25, 15, height-35
    mid = (top+bottom)/2
    canvas.create_line(left, mid, right, mid, fill='#777', dash=(4, 3))
    for key, color in (('first_gain','#2563eb'), ('second_gain','#ea580c')):
        last = None
        for i, p in enumerate(points):
            val = p[key]
            if val is None:
                last = None
                continue
            x = left + i * (right-left)/max(1,len(points)-1)
            y = mid - val/scale * (bottom-top)*.43
            if last is not None:
                canvas.create_line(*last, x, y, fill=color, width=2)
            canvas.create_oval(x-3,y-3,x+3,y+3,fill=color,outline=color)
            last = (x,y)
    canvas.create_text(left+65,height-12,text='Bleu : première campagne',fill='#2563eb')
    canvas.create_text(left+260,height-12,text='Orange : seconde campagne',fill='#ea580c')
