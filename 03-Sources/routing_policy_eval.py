"""Offline, deterministic comparison of conservative routing gate policies.

Author: Abdelhalim Talbi. Never authorizes path reuse or changes routing output.
"""
from dataclasses import dataclass
from statistics import median

@dataclass(frozen=True)
class GatePolicy:
    name: str
    hard_limit: int = 8
    min_edits: int = 8
    ratio: float = .20
    observations: int = 3
    cost_ratio: float = 1.5
    min_validation_seconds: float = .001

    def __post_init__(self):
        if (self.hard_limit < 1 or self.min_edits < 1 or self.observations < 1
                or not 0 <= self.ratio <= 1 or self.cost_ratio <= 0
                or self.min_validation_seconds < 0):
            raise ValueError('Invalid gate policy')


def should_full_route(policy, edits, nodes, samples):
    """Pure evaluation: returns (fallback, reason); no unsafe reuse possible."""
    if edits >= policy.hard_limit:
        return True, 'hard_limit'
    if nodes <= 0 or edits < policy.min_edits or edits / nodes < policy.ratio:
        return False, 'insufficient_edit_density'
    measured = [s for s in samples if s.get('validation_seconds', 0) >= policy.min_validation_seconds
                and s.get('routing_seconds', 0) > 0]
    if len(measured) < policy.observations:
        return False, 'insufficient_measurements'
    recent = measured[-policy.observations:]
    if (all(s.get('reused', 0) == 0 for s in recent)
            and median(s['validation_seconds'] for s in recent)
            > policy.cost_ratio * median(s['routing_seconds'] for s in recent)):
        return True, 'measured_cost'
    return False, 'reuse_or_cost_favorable'


def compare_policies(scenarios, policies):
    """Compare gate decisions on identical traces; no synthetic speedup claims."""
    report = []
    for p in policies:
        decisions = []
        for scenario in scenarios:
            fallback, reason = should_full_route(p, scenario['edits'], scenario['nodes'], scenario.get('samples', []))
            decisions.append({'id': scenario['id'], 'full_route': fallback, 'reason': reason})
        report.append({'policy': p.name, 'full_routes': sum(d['full_route'] for d in decisions),
                       'partial_eligible': sum(not d['full_route'] for d in decisions), 'decisions': decisions})
    return report


DEFAULT_POLICIES = (
    GatePolicy('v5.18_default'),
    GatePolicy('density_05pct', hard_limit=8, min_edits=4, ratio=.05),
    GatePolicy('conservative_6edits', hard_limit=6, min_edits=4, ratio=.15),
    GatePolicy('cost_strict', hard_limit=8, min_edits=4, ratio=.10, observations=4, cost_ratio=2.0),
)
