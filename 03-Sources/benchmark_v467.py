"""Reproducible SQLite pagination benchmark; no performance promises. Author: Abdelhalim Talbi."""
import argparse,json,sqlite3,time,statistics,platform
from pathlib import Path
from cursor_pagination import decision_page
class Fixture:
    def __init__(self,db):self.db=db
    def verify_audit(self):return True  # synthetic benchmark only; no audit data generated

def run(n,iterations=5):
    db=sqlite3.connect(':memory:')
    db.execute('CREATE TABLE decisions(id TEXT PRIMARY KEY,title TEXT,status TEXT,author TEXT)')
    db.executemany('INSERT INTO decisions VALUES(?,?,?,?)',((f'D-{i:09}',f'Design {i}','PROPOSED','bench') for i in range(n)))
    db.commit();g=Fixture(db)
    timings={}
    for label,fn in [('offset_end',lambda:db.execute('SELECT id FROM decisions ORDER BY id LIMIT 50 OFFSET ?', (max(0,n-50),)).fetchall()),('keyset_end',lambda:decision_page(g,50, __import__('cursor_pagination')._encode(f'D-{max(0,n-51):09}'))),('keyset_start',lambda:decision_page(g,50))]:
        samples=[]
        for _ in range(iterations):
            t=time.perf_counter();fn();samples.append((time.perf_counter()-t)*1000)
        timings[label]={'median_ms':round(statistics.median(samples),4),'min_ms':round(min(samples),4),'max_ms':round(max(samples),4)}
    return {'rows':n,'measurements':timings}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--sizes',nargs='+',type=int,default=[1000,10000,100000]);p.add_argument('--iterations',type=int,default=5);p.add_argument('--output',default='benchmark-v467.json');a=p.parse_args()
    if not 1<=a.iterations<=100 or any(not 1<=n<=1000000 for n in a.sizes):p.error('Invalid size/iterations')
    result={'environment':{'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'platform':platform.platform()},'method':'synthetic in-memory SQLite; no real audit; wall-clock perf_counter; timings vary','results':[run(n,a.iterations) for n in a.sizes]}
    Path(a.output).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
