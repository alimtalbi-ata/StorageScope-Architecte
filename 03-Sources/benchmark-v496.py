import json,time,random
from graph_layout import scalable_obstacle_routes
results=[]
for n in (500,1000,2000):
    rng=random.Random(496)
    positions=[(str(i),(i%40)*235+rng.randrange(-8,9),160+(i//40)*95) for i in range(n)]
    start=time.perf_counter()
    routes=scalable_obstacle_routes(positions,100,recent_routes=24)
    results.append({'dependencies':n,'routes':len(routes),'routing_seconds':round(time.perf_counter()-start,3)})
print(json.dumps({'environment':'Linux headless, synthetic routing only, one run per size','results':results},indent=2))
