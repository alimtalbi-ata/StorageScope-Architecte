"""Repeated sequence benchmark: cost-aware cache versus exact full recompute."""
import json, statistics, time
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes

def run(n, edits, spacing, repetition):
    base=[(str(i),i*spacing,250) for i in range(n)]
    cache=PartialGeometryRoutingCache(capacity=2)
    cache.route(base,0,recent_routes=8)
    workload=(min(8,n//100),edits,8)
    # Controlled adverse prior measurements, NOT results from this run.
    cache.workload_timing[workload]=[dict(validation_seconds=.3,routing_seconds=.01,reused=0) for _ in range(2)]
    rows=[]
    for step in range(5):
        points=list(base)
        for j in range(edits):
            idx=n//2+j*2
            points[idx]=(str(idx),idx*spacing+step+1+j,250)
        start=time.perf_counter(); result=cache.route(points,0,recent_routes=8); elapsed=time.perf_counter()-start
        start=time.perf_counter(); reference=scalable_obstacle_routes(points,0,recent_routes=8); full=time.perf_counter()-start
        assert result==reference
        rows.append(dict(cache_ms=elapsed*1000,full_ms=full*1000,decision=cache.last_cost_gate_decision))
    return dict(nodes=n,edits=edits,spacing=spacing,repetition=repetition,cache_median_ms=statistics.median(x['cache_ms'] for x in rows),full_median_ms=statistics.median(x['full_ms'] for x in rows),cost_skips=cache.cost_gate_skips,cost_probes=cache.cost_gate_probes,comparisons=len(rows))

if __name__=='__main__':
    results=[run(n,e,s,r) for n in (100,300) for e in (1,3,8) for s in (115,260) for r in range(2)]
    grouped=[]
    for n in (100,300):
        for e in (1,3,8):
            for s in (115,260):
                subset=[x for x in results if (x['nodes'],x['edits'],x['spacing'])==(n,e,s)]
                grouped.append(dict(nodes=n,edits=e,spacing=s,cache_median_ms=round(statistics.median(x['cache_median_ms'] for x in subset),3),full_median_ms=round(statistics.median(x['full_median_ms'] for x in subset),3),comparisons=sum(x['comparisons'] for x in subset),cost_skips=sum(x['cost_skips'] for x in subset)))
    with open('benchmark-v516.json','w') as f:json.dump(dict(method='2 repetitions per 12 scenarios; 5 successive edits each; seeded synthetic adverse timing history; paired exact full-route comparison; timings include cache and validation; Linux headless',scenarios=grouped,runs=results),f,indent=2)
    for x in grouped:print(x)
