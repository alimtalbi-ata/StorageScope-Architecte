"""Conservative, vendor-aware identity matching; never merges assets."""
from __future__ import annotations
import re
from collections import defaultdict

FIELDS = ('serial', 'wwn', 'uuid')
VENDORS = {'pure storage':'pure','pure':'pure','netapp':'netapp','dell emc':'dell','dell':'dell','emc':'dell','hpe':'hpe','hp':'hpe','ibm':'ibm','hitachi vantara':'hitachi','hitachi':'hitachi'}

def norm(value):
    return re.sub(r'[^a-z0-9]', '', value.casefold()) if isinstance(value,str) else ''

def vendor(value):
    return VENDORS.get(str(value).strip().casefold(), norm(value)) if value else ''

def analyze(records):
    if not isinstance(records,list): raise ValueError('records must be a list')
    groups=defaultdict(list); invalid=[]
    for i,r in enumerate(records):
        if not isinstance(r,dict): invalid.append({'index':i,'reason':'not_object'}); continue
        if not isinstance(r.get('source'),str) or not r['source'].strip(): invalid.append({'index':i,'reason':'missing_source'})
        for f in FIELDS:
            n=norm(r.get(f))
            if n: groups[(f,n)].append(i)
    pairs=defaultdict(set)
    for (f,_),indices in groups.items():
        for j,a in enumerate(indices):
            for b in indices[j+1:]: pairs[(a,b)].add(f)
    candidates=[]
    for (i,j),matches in sorted(pairs.items()):
        a,b=records[i],records[j]
        contradictions=[]
        for f in FIELDS:
            x,y=norm(a.get(f)),norm(b.get(f))
            if x and y and x!=y: contradictions.append(f)
        va,vb=vendor(a.get('vendor')),vendor(b.get('vendor'))
        if va and vb and va!=vb: contradictions.append('vendor')
        kinds=[str(r.get('type','')).strip().casefold() for r in (a,b)]
        if all(kinds) and kinds[0]!=kinds[1]: contradictions.append('type')
        conflicts=[f for f in sorted(set(a)&set(b)-set(FIELDS)-{'source','updated_at'}) if a[f] is not None and b[f] is not None and a[f]!=b[f]]
        candidates.append({'indices':[i,j], 'matching_identifiers':sorted(matches), 'contradictions':sorted(contradictions), 'attribute_conflicts':conflicts,'status':'BLOCKED_CONTRADICTION' if contradictions else 'REVIEW_REQUIRED'})
    return {'schema':'storagescope.identity.v1','candidates':candidates,'invalid_records':invalid,'automatic_merges':0}
