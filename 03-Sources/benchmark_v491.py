"""Headless pipeline benchmark; excludes Tk and disk/SQLite IO. Abdelhalim Talbi."""
import json,time,statistics
from pathlib import Path
from graph_layout import layout_grouped, scalable_obstacle_routes
from graph_spatial import card_index,route_index

def measure(n):
    nodes=[(('ACTION',str(i),'OPEN',False)) for i in range(n)]
    times=[]; summary=None
    for _ in range(3):
        t=time.perf_counter()
        positions,w,h=layout_grouped(nodes,900,3)
        a=time.perf_counter()
        routes=scalable_obstacle_routes(positions,w/2)
        b=time.perf_counter()
        ci=card_index(positions);ri=route_index(routes)
        visible=ci.query((0,0,900,700),1.0); links=ri.query((0,0,900,700),1.0)
        c=time.perf_counter()
        times.append([(a-t)*1000,(b-a)*1000,(c-b)*1000])
        summary={'cards':len(positions),'routes':len(routes),'visible_cards':len(visible),'visible_routes':len(links)}
    summary['median_ms']={k:round(statistics.median(x[i] for x in times),3) for i,k in enumerate(('layout','routing','index_and_query'))}
    return summary
if __name__=='__main__':
    result={'scope':'synthetic in-memory layout, routing, spatial query; excludes SQLite and Tk','runs':3,'sizes':{str(n):measure(n) for n in (100,500,1000)}}
    Path(__file__).with_name('benchmark-result-v491.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
