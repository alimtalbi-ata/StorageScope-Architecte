"""Repeatable policy comparison on identical synthetic traces; no timing claims."""
import json
from routing_policy_eval import compare_policies, DEFAULT_POLICIES

scenarios = []
for n in (100, 300):
    for edits in (1, 3, 5, 6, 7, 8):
        for density in ('spaced', 'dense'):
            for cost in ('favorable', 'adverse'):
                samples = [dict(validation_seconds=.003 if cost == 'favorable' else .03,
                                routing_seconds=.01, reused=1 if cost == 'favorable' else 0) for _ in range(4)]
                scenarios.append(dict(id=f'{n}-{edits}-{density}-{cost}', nodes=n, edits=edits, samples=samples))
report = dict(method='Offline gate-decision comparison on 48 identical synthetic traces; no measured performance gain',
              scenarios=len(scenarios), policies=compare_policies(scenarios, DEFAULT_POLICIES))
with open('benchmark-v519.json', 'w') as f: json.dump(report, f, indent=2)
for p in report['policies']:
    print(p['policy'], 'full=', p['full_routes'], 'partial_eligible=', p['partial_eligible'])
