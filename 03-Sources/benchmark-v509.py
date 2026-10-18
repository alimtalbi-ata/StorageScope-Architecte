"""Reproducible repeated synthetic dense/sparse multi-edit benchmark; no GUI."""
import argparse, json, random, statistics, time
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes

def run(sizes=(100,300), repeats=3, seed=509):
    rows=[]
    for n in sizes:
        for density, spacing in [('sparse',260),('dense',115)]:
            for edits in (1,3,8):
                samples=[]
                for repetition in range(repeats):
                    rng=random.Random(seed+n*100+edits*10+repetition+(0 if density=='sparse' else 1))
                    old=[(str(i),300+i*spacing,210+(i%4)*55) for i in range(n)]
                    updated=list(old)
                    # Avoid first three nodes, favor edits distributed through graph
                    for j in rng.sample(range(3,n),edits):
                        name,x,y=updated[j];updated[j]=(name,x+rng.choice([-15,15]),y+rng.choice([-8,8]))
                    cache=PartialGeometryRoutingCache();cache.route(old,0,recent_routes=8)
                    start=time.perf_counter(); actual=cache.route(updated,0,recent_routes=8); partial=time.perf_counter()-start
                    start=time.perf_counter(); expected=scalable_obstacle_routes(updated,0,recent_routes=8); full=time.perf_counter()-start
                    if actual != expected: raise AssertionError((n,density,edits,repetition))
                    samples.append(dict(partial=partial,full=full,**cache.last_routing_stats,skipped=cache.validation_skips))
                rows.append(dict(nodes=n,density=density,edits=edits,repeats=repeats,
                                 partial_median_seconds=round(statistics.median(x['partial'] for x in samples),6),
                                 full_median_seconds=round(statistics.median(x['full'] for x in samples),6),
                                 reused_median=statistics.median(x['prefix_reused']+x['suffix_reused'] for x in samples),
                                 skipped_runs=sum(x['skipped']>0 for x in samples),
                                 samples=samples))
    return rows

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--sizes',nargs='+',type=int,default=[100,300]);parser.add_argument('--repeats',type=int,default=3)
    args=parser.parse_args();print(json.dumps(run(args.sizes,args.repeats),indent=2))
