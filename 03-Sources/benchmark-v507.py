"""Synthetic multi-change routing benchmarks, Linux headless."""
import json,time,statistics
from graph_layout import PartialGeometryRoutingCache,scalable_obstacle_routes
results=[]
for n in (100,300,600):
 for changes in (1,3,8):
  old=[(str(i),400+i*260,350) for i in range(n)]
  indices=[max(0,n-1-k*(max(1,n//(changes+1)))) for k in range(changes)]
  new=list(old)
  for i in indices:new[i]=(str(i),new[i][1]+12,new[i][2])
  cache=PartialGeometryRoutingCache();cache.route(old,100,recent_routes=8)
  t=time.perf_counter();part=cache.route(new,100,recent_routes=8);pt=time.perf_counter()-t
  t=time.perf_counter();full=scalable_obstacle_routes(new,100,recent_routes=8);ft=time.perf_counter()-t
  assert part==full
  results.append(dict(nodes=n,changes=changes,partial_seconds=round(pt,5),full_seconds=round(ft,5),checks=cache.validation_checks,skips=cache.validation_skips,attempts=cache.validation_attempts,calibrated_budget=cache.calibrate_validation_budget()))
print(json.dumps(results,indent=2))
