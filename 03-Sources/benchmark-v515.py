"""Reproducible cost-gate sequence, with independent full-route equality checks."""
import json, statistics, time
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes

def run(n, edits, spacing):
    base=[(str(i),i*spacing,250) for i in range(n)]
    cache=PartialGeometryRoutingCache(capacity=2)
    cache.route(base,0,recent_routes=8)
    workload=(min(8,n//100),edits,8)
    cache.workload_timing[workload]=[dict(validation_seconds=.3,routing_seconds=.01,reused=0) for _ in range(3)]
    rows=[]
    for step in range(10):
        points=list(base)
        for j in range(edits):
            idx=n//2+j*2
            points[idx]=(str(idx),idx*spacing+step+1+j,250)
        start=time.perf_counter()
        result=cache.route(points,0,recent_routes=8)
        elapsed=time.perf_counter()-start
        start=time.perf_counter()
        reference=scalable_obstacle_routes(points,0,recent_routes=8)
        full=time.perf_counter()-start
        assert result==reference
        rows.append(dict(step=step,cache_seconds=elapsed,full_seconds=full,decision=cache.last_cost_gate_decision,reused=sum(cache.last_routing_stats.get(k,0) for k in ('prefix_reused','suffix_reused'))))
    return dict(nodes=n,edits=edits,spacing=spacing,median_cache_seconds=statistics.median(r['cache_seconds'] for r in rows),median_full_seconds=statistics.median(r['full_seconds'] for r in rows),cost_skips=cache.cost_gate_skips,cost_probes=cache.cost_gate_probes,validated_comparisons=len(rows),samples=rows)

if __name__=='__main__':
    results=[run(n,e,spacing) for n in (100,300) for e in (1,3,8) for spacing in (115,260)]
    with open('benchmark-v515.json','w') as f:json.dump(dict(description='Synthetic seeded-by-formula deterministic layouts, wall-clock timings fluctuate; equality against full router.',results=results),f,indent=2)
    for r in results:print(r['nodes'],r['edits'],r['spacing'],round(r['median_cache_seconds']*1000,2),round(r['median_full_seconds']*1000,2),r['cost_skips'],r['cost_probes'])
