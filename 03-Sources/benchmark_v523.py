"""Measured, reproducible paired policy benchmark. Author: Abdelhalim Talbi."""
import csv, json, statistics, time
from pathlib import Path
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes
from routing_policy_performance import evaluate_performance


def run(output_dir='.', repetitions=3):
    out=Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    pairs=[]
    for n in (40, 80):
        for edits in (1, 3, 6, 8):
            for spacing in (115, 260):
                for repetition in range(repetitions):
                    positions=[(str(i), i*spacing, 250) for i in range(n)]
                    modified=list(positions)
                    for j in range(edits):
                        i=n//3+j*2
                        modified[i]=(str(i), i*spacing+repetition+j+1, 250)
                    reference=scalable_obstacle_routes(modified,0,recent_routes=8)
                    measurements={}
                    # Alternate execution order to limit systematic ordering bias.
                    for name in (('baseline','candidate') if repetition%2==0 else ('candidate','baseline')):
                        cache=PartialGeometryRoutingCache(capacity=2)
                        cache.high_edit_threshold=8 if name=='baseline' else 6
                        cache.route(positions,0,recent_routes=8)
                        t=time.perf_counter()
                        actual=cache.route(modified,0,recent_routes=8)
                        elapsed=time.perf_counter()-t
                        measurements[name]=(elapsed,actual==reference,cache.high_edit_fallbacks)
                    pair=dict(id=f'{n}-{edits}-{spacing}-{repetition}',nodes=n,edits=edits,spacing=spacing,
                              repetition=repetition,baseline_seconds=measurements['baseline'][0],
                              candidate_seconds=measurements['candidate'][0],
                              routes_equal=measurements['baseline'][1] and measurements['candidate'][1],
                              baseline_fallbacks=measurements['baseline'][2],candidate_fallbacks=measurements['candidate'][2])
                    pairs.append(pair)
    from benchmark_analysis_v524 import summarize
    analysis=summarize(pairs)
    decision=evaluate_performance(pairs)
    report=dict(method='Actual perf_counter wall times on Linux headless; warm cache per policy; paired inputs; execution order alternated; no production activation; synthetic topology; environment dependent',
                baseline='high_edit_threshold=8',candidate='high_edit_threshold=6',
                repetitions=repetitions,comparison_count=len(pairs),all_routes_equal=all(p['routes_equal'] for p in pairs),
                median_baseline_ms=round(1000*statistics.median(p['baseline_seconds'] for p in pairs),3),
                median_candidate_ms=round(1000*statistics.median(p['candidate_seconds'] for p in pairs),3),
                decision=decision,category_analysis=analysis,pairs=pairs)
    (out/'benchmark-v524.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (out/'benchmark-v523.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    with (out/'benchmark-v523.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(pairs[0]));writer.writeheader();writer.writerows(pairs)
    return report

if __name__=='__main__':
    report=run()
    print('pairs=',report['comparison_count'],'equal=',report['all_routes_equal'], 'decision=',report['decision']['reason'])
    print('median baseline/candidate ms=',report['median_baseline_ms'],report['median_candidate_ms'])
