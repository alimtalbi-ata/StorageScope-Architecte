"""Synthetic Linux benchmark; run: python benchmark-v506.py"""
import json,time,statistics
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes
out=[]
for n in (100,300,520,1000):
    old=[(str(i),400+i*260,350) for i in range(n)]
    new=list(old); new[-1]=(new[-1][0],new[-1][1]+10,new[-1][2])
    cache=PartialGeometryRoutingCache();cache.route(old,100,recent_routes=0)
    t=time.perf_counter();partial=cache.route(new,100,recent_routes=0);pt=time.perf_counter()-t
    t=time.perf_counter();full=scalable_obstacle_routes(new,100,recent_routes=0);ft=time.perf_counter()-t
    assert partial==full
    out.append(dict(nodes=n,partial_seconds=round(pt,4),full_seconds=round(ft,4),validation_checks=cache.validation_checks,validation_skips=cache.validation_skips))
print(json.dumps(out,indent=2))
