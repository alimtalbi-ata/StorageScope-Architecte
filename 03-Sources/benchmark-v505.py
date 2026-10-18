"""Reproducible headless full-vs-partial benchmark; author Abdelhalim Talbi."""
import json, time, argparse
parser=argparse.ArgumentParser()
parser.add_argument("--include-5000",action="store_true")
args=parser.parse_args()
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes
rows=[]
for n in ((1000,2000,5000) if args.include_5000 else (1000,2000)):
    old=[(str(i),400+(i%50)*440,350+(i//50)*300) for i in range(n)]
    new=list(old); mid=n//2
    new[mid]=(new[mid][0],new[mid][1]+20,new[mid][2])
    cache=PartialGeometryRoutingCache()
    t=time.perf_counter(); cache.route(old,100,recent_routes=8); initial=time.perf_counter()-t
    t=time.perf_counter(); partial=cache.route(new,100,recent_routes=8); partial_time=time.perf_counter()-t
    t=time.perf_counter(); full=scalable_obstacle_routes(new,100,recent_routes=8); full_time=time.perf_counter()-t
    rows.append({'dependencies':n,'initial_seconds':round(initial,4),'partial_seconds':round(partial_time,4),'full_seconds':round(full_time,4),'speedup':round(full_time/partial_time,2) if partial_time else None,'identical':partial==full,'reused_prefixes':cache.partial_reuses,'reused_suffix_paths':cache.suffix_reuses})
    print(rows[-1],flush=True)
with open('benchmark-v505.json','w') as f: json.dump(rows,f,indent=2)
