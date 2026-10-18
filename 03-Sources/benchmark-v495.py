import json,random,statistics,time
from graph_layout import ObstacleBucketIndex,_fast_route_hits_rect
rng=random.Random(495)
results=[]
for n in (500,1000,5000):
    rects=[(x,y,x+190,y+48) for x,y in ((rng.randrange(-4000,4000),rng.randrange(0,6000)) for _ in range(n))]
    paths=[]
    for _ in range(100):
        x,y=rng.randrange(-4000,4000),rng.randrange(0,6000)
        paths.append([(x,y),(x+300,y),(x+300,y+250)])
    linear=[];indexed=[]
    for _ in range(3):
        start=time.perf_counter()
        expected=[{i for i,r in enumerate(rects) if _fast_route_hits_rect(p,r)} for p in paths]
        linear.append(time.perf_counter()-start)
        start=time.perf_counter(); idx=ObstacleBucketIndex(rects)
        actual=[idx.query(p) for p in paths]
        indexed.append(time.perf_counter()-start)
        assert expected==actual
    results.append({'rectangles':n,'queries':100,'linear_ms':round(statistics.median(linear)*1000,2),'indexed_build_included_ms':round(statistics.median(indexed)*1000,2)})
print(json.dumps({'environment':'Synthetic Linux headless; no Tk UI; includes index build', 'results':results},indent=2))
