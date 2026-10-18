"""Reproducible routing benchmark. Author: Abdelhalim Talbi."""
import json, time
from graph_layout import scalable_obstacle_routes


def benchmark(sizes=(100,500,1000)):
    results=[]
    for n in sizes:
        nodes=[(('ACTION',str(i),'',False),120+(i%8)*225,140+(i//8)*80) for i in range(n)]
        start=time.perf_counter()
        paths=scalable_obstacle_routes(nodes,900)
        elapsed=time.perf_counter()-start
        results.append({'nodes':n,'seconds':round(elapsed,4),'paths':len(paths)})
    return results

if __name__=='__main__':
    print(json.dumps(benchmark(),indent=2))
