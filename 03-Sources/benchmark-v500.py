"""Headless reproducible cache benchmark; author Abdelhalim Talbi."""
import json,time,statistics
from graph_layout import RoutingResultCache
rows=[]
for n in (500,1000):
    positions=[(str(i),(i%40)*220,160+(i//40)*90) for i in range(n)]
    cache=RoutingResultCache()
    t=time.perf_counter(); cache.route(positions,110); cold=time.perf_counter()-t
    hits=[]
    for _ in range(5):
        t=time.perf_counter();cache.route(positions,110);hits.append(time.perf_counter()-t)
    rows.append({'dependencies':n,'cold_seconds':round(cold,5),'warm_median_seconds':round(statistics.median(hits),5),'cache_hits':cache.hits})
print(json.dumps(rows,indent=2))
