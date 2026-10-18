"""Headless spatial query benchmark; not a Windows UI FPS benchmark."""
import json,time,statistics
from graph_spatial import card_index
from graph_viewport import visible_cards
out={}
for n in (100,500,1000,5000):
    positions=[(('ACTION',str(i),'OPEN',False),i%50*220,i//50*90) for i in range(n)]
    start=time.perf_counter();index=card_index(positions);build=(time.perf_counter()-start)*1000
    views=[(i*35,i*25,i*35+900,i*25+650) for i in range(100)]
    t=time.perf_counter()
    for b in views: visible_cards(positions,b)
    linear=(time.perf_counter()-t)*1000
    t=time.perf_counter()
    for b in views: index.query(b)
    indexed=(time.perf_counter()-t)*1000
    out[str(n)]={'build_ms':round(build,3),'100_linear_queries_ms':round(linear,3),'100_indexed_queries_ms':round(indexed,3),'speedup':round(linear/indexed,2)}
print(json.dumps(out,indent=2))
