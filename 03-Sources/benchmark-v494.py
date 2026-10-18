import json, random, statistics, time
from graph_layout import RecentSegmentIndex, _indexed_interference, _route_segments
rng=random.Random(494)
results=[]
for n in (24, 96, 256):
    routes=[]
    for i in range(n):
        x,y=rng.randrange(-1000,1000),rng.randrange(-1000,1000)
        routes.append([(x,y),(x,y+120),(x+120,y+120)])
    segments=[_route_segments(p) for p in routes]
    candidates=routes[:min(30,n)]
    old=[]; new=[]
    for _ in range(5):
        t=time.perf_counter()
        reference=[_indexed_interference(segments,c) for c in candidates]
        old.append(time.perf_counter()-t)
        t=time.perf_counter(); index=RecentSegmentIndex(segments)
        indexed=[index.score(c) for c in candidates]
        new.append(time.perf_counter()-t)
        assert reference==indexed
    results.append({'recent_routes':n,'candidates':len(candidates),'linear_ms':round(statistics.median(old)*1000,3),'indexed_including_build_ms':round(statistics.median(new)*1000,3)})
print(json.dumps({'environment':'Linux headless synthetic; not Windows Tkinter', 'results':results},indent=2))
