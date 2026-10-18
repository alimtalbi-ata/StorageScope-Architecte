import json,sys,time,platform
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_desktop import filter_candidates
results=[]
for n in (10000,100000):
 rows=[(f'key-{i}',{'asset_ids':[f'netapp-{i}'],'review_eligibility':'BLOCKED_CONTRADICTION' if i%10==0 else 'REVIEW_REQUIRED','notes':f'site {i%20}'}) for i in range(n)]
 for q,state in [('', 'ALL'),('', 'BLOCKED_CONTRADICTION'),('asset:netapp-999','ALL'),('site 4','ALL')]:
  t=time.perf_counter();found=filter_candidates(rows,q,state);elapsed=(time.perf_counter()-t)*1000
  results.append(dict(size=n,query=q,state=state,matches=len(found),elapsed_ms=round(elapsed,2)))
print(json.dumps({'platform':platform.platform(),'results':results},indent=2))
