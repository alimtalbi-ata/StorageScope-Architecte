"""Offline paired runtime evidence gate; no production routing activation.
Author: Abdelhalim Talbi.
"""
import math
from statistics import median
from routing_policy_selector import DEFAULT


def evaluate_performance(pairs, *, min_pairs=12, min_gain=.05, max_regression=.10):
    """Compare paired measured durations; fail closed on missing/unsafe evidence.

    Each pair has id, baseline_seconds, candidate_seconds, routes_equal (verified
    equality of complete output, not merely eligible routing decisions).
    """
    base = dict(selected_policy=DEFAULT, recommendation_only=True,
                production_activation=False, reason='invalid_input',
                sample_count=0, median_gain=None, worst_regression=None)
    if (isinstance(min_pairs, bool) or not isinstance(min_pairs, int) or min_pairs < 2
            or not all(isinstance(x, (int, float)) and not isinstance(x, bool)
                       and math.isfinite(x) and 0 <= x < 1 for x in (min_gain, max_regression))
            or not isinstance(pairs, (list, tuple))):
        return base
    base['sample_count'] = len(pairs)
    ids = set()
    gains = []
    for pair in pairs:
        if not isinstance(pair, dict) or not isinstance(pair.get('id'), (str, int)) or isinstance(pair.get('id'), bool):
            return base
        key = str(pair['id'])
        if not key or key in ids:
            return base
        ids.add(key)
        if pair.get('routes_equal') is not True:
            return {**base, 'reason': 'route_mismatch_or_unverified'}
        b, c = pair.get('baseline_seconds'), pair.get('candidate_seconds')
        if any(isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x) or x <= 0 for x in (b, c)):
            return base
        gains.append((b - c) / b)
    if len(gains) < min_pairs:
        return {**base, 'reason': 'insufficient_paired_measurements'}
    med = median(gains)
    worst = max(0.0, -min(gains))
    base.update(median_gain=med, worst_regression=worst)
    if worst > max_regression:
        return {**base, 'reason': 'regression_guard'}
    if med < min_gain:
        return {**base, 'reason': 'gain_below_threshold'}
    return {**base, 'selected_policy': 'candidate_measured', 'reason': 'measured_candidate_preferred'}
