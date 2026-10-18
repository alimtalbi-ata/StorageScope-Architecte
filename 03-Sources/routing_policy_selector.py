"""Conservative, explainable offline routing policy recommendations.

No production activation or cached-path authorization. Author: Abdelhalim Talbi.
"""
import math
from collections.abc import Mapping, Sequence
from routing_policy_eval import DEFAULT_POLICIES, GatePolicy, compare_policies

DEFAULT = 'v5.18_default'


def _validate(scenarios, policies, min_scenarios):
    errors = []
    if isinstance(min_scenarios, bool) or not isinstance(min_scenarios, int) or min_scenarios < 1:
        errors.append('min_scenarios_must_be_positive_integer')
    if not isinstance(scenarios, (list, tuple)):
        return ['scenarios_must_be_list_or_tuple'] + errors
    if not isinstance(policies, (list, tuple)) or not policies:
        errors.append('policies_must_be_nonempty_sequence')
    else:
        names = []
        for i, p in enumerate(policies):
            if not isinstance(p, GatePolicy):
                errors.append(f'policy_{i}_invalid_type')
            else:
                names.append(p.name)
        if len(names) != len(set(names)):
            errors.append('duplicate_policy_names')
        if DEFAULT not in names:
            errors.append('default_policy_missing')
    ids = set()
    for i, s in enumerate(scenarios):
        if not isinstance(s, Mapping):
            errors.append(f'scenario_{i}_invalid_type'); continue
        sid = s.get('id')
        if not isinstance(sid, (str, int)) or isinstance(sid, bool) or not str(sid):
            errors.append(f'scenario_{i}_invalid_id')
        elif str(sid) in ids:
            errors.append(f'scenario_{i}_duplicate_id')
        else:
            ids.add(str(sid))
        for field, lower in (('nodes', 1), ('edits', 0)):
            val = s.get(field)
            if isinstance(val, bool) or not isinstance(val, int) or val < lower:
                errors.append(f'scenario_{i}_invalid_{field}')
        samples = s.get('samples', [])
        if not isinstance(samples, (list, tuple)):
            errors.append(f'scenario_{i}_invalid_samples'); continue
        for j, sample in enumerate(samples):
            if not isinstance(sample, Mapping):
                errors.append(f'scenario_{i}_sample_{j}_invalid_type'); continue
            for field in ('validation_seconds', 'routing_seconds', 'reused'):
                val = sample.get(field, 0)
                if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or val < 0:
                    errors.append(f'scenario_{i}_sample_{j}_invalid_{field}')
    return errors


def select_policy(scenarios, policies=DEFAULT_POLICIES, *, min_scenarios=24):
    """Return fail-closed recommendation with explicit evidence and limitations."""
    errors = _validate(scenarios, policies, min_scenarios)
    count = len(scenarios) if isinstance(scenarios, (list, tuple)) else 0
    base = {'selected_policy': DEFAULT, 'sample_count': count,
            'recommendation_only': True, 'production_activation': False,
            'limitations': ['Offline decisions only; no measured runtime speedup.',
                            'Partial eligibility does not prove route safety or performance.'],
            'validation_errors': errors, 'comparison': []}
    if errors:
        return {**base, 'reason': 'invalid_input', 'explanation': 'Invalid traces or policies: default retained.'}
    if count < min_scenarios:
        return {**base, 'reason': 'insufficient_scenarios', 'minimum_scenarios': min_scenarios,
                'explanation': f'{count} scenarios; at least {min_scenarios} required.'}
    report = compare_policies(scenarios, policies)
    by_name = {r['policy']: r for r in report}
    default = by_name[DEFAULT]
    complete = [r for r in report if len(r['decisions']) == count]
    best = min(complete, key=lambda r: (r['full_routes'], r['policy'])) if complete else default
    if best['full_routes'] >= default['full_routes']:
        best = default
        reason = 'no_strict_improvement'
    else:
        reason = 'fewer_full_route_decisions'
    return {**base, 'selected_policy': best['policy'], 'reason': reason,
            'full_routes': best['full_routes'], 'default_full_routes': default['full_routes'],
            'avoided_full_route_decisions': default['full_routes'] - best['full_routes'],
            'comparison': [{'policy': r['policy'], 'full_routes': r['full_routes'],
                            'partial_eligible': r['partial_eligible']} for r in report],
            'explanation': ('Selected on fewer offline full-route decisions, not measured speed.'
                            if reason == 'fewer_full_route_decisions' else
                            'No candidate strictly improves fallback count; default retained.')}
