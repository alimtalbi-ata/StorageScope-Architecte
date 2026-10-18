"""Synthetic Python-only table row preparation; NOT a Tkinter/Windows UI benchmark."""
import sys, pathlib, time, statistics, json
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'03-Sources'))
from governance_desktop import paginate_candidates, display_assets
result={}
for n in (10000,100000):
 candidates=[(i, f'KEY-{i:09d}', {'asset_ids':[f'netapp-{i:09d}',f'san-{i%32}'],'review_eligibility':'REVIEW_REQUIRED'}) for i in range(n)]
 for page in (0,(n-1)//100):
  samples=[]
  for _ in range(7):
   start=time.perf_counter()
   rows=[(str(i),key if len(key)<=36 else key[:35]+'…',display_assets(c),c.get('review_eligibility','REVIEW_REQUIRED')) for i,key,c in paginate_candidates(candidates,page)]
   samples.append((time.perf_counter()-start)*1000)
  result[f'{n}_page_{page}']={'rows':len(rows),'median_ms':round(statistics.median(samples),5)}
print(json.dumps({'environment':'Python only; no Tkinter widget created','results':result},indent=2))
