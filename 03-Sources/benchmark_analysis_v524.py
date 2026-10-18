"""Paired benchmark dispersion and category-level conservative analysis.
Author: Abdelhalim Talbi.
"""
import math
from collections import defaultdict
from statistics import median
from routing_policy_performance import evaluate_performance


def summarize(pairs, min_group_samples=3):
    if not isinstance(pairs, (list, tuple)) or not isinstance(min_group_samples, int) or isinstance(min_group_samples, bool) or min_group_samples < 2:
        raise ValueError('invalid benchmark inputs')
    seen=set(); groups=defaultdict(list)
    for pair in pairs:
        if not isinstance(pair, dict) or not isinstance(pair.get('id'), str) or not pair['id'] or pair['id'] in seen:
            raise ValueError('duplicate or invalid pair id')
        seen.add(pair['id'])
        if pair.get('routes_equal') is not True:
            raise ValueError('unverified or unequal routes')
        b=pair.get('baseline_seconds'); c=pair.get('candidate_seconds')
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in (b,c)):
            raise ValueError('invalid duration')
        category=(pair.get('nodes'),pair.get('edits'),pair.get('spacing'))
        if any(isinstance(v,bool) or not isinstance(v,int) or v<=0 for v in category):
            raise ValueError('invalid category')
        groups[category].append((b-c)/b)
    categories=[]
    for (nodes,edits,spacing), gains in sorted(groups.items()):
        ordered=sorted(gains); n=len(ordered)
        categories.append(dict(nodes=nodes,edits=edits,spacing=spacing,samples=n,
            median_gain=median(ordered),minimum_gain=ordered[0],maximum_gain=ordered[-1],
            spread=ordered[-1]-ordered[0],
            q1=ordered[(n-1)//4],q3=ordered[(3*(n-1))//4],
            sufficient=n>=min_group_samples))
    decision=evaluate_performance(pairs)
    # Never promote a candidate with a category lacking repeated evidence.
    if decision['selected_policy'] != 'candidate_measured':
        reason=decision['reason']
    elif any(not c['sufficient'] for c in categories):
        reason='insufficient_category_repetitions'
    elif any(c['median_gain'] < 0 for c in categories):
        reason='category_median_regression'
    else:
        reason='candidate_passes_category_guard'
    return dict(recommendation_only=True,production_activation=False,
                selected_policy='candidate_measured' if reason=='candidate_passes_category_guard' else 'default',
                reason=reason,global_gate=decision,categories=categories,
                category_count=len(categories),pair_count=len(pairs))
