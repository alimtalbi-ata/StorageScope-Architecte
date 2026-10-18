"""Deterministic cross-version search benchmark. Not a GUI benchmark."""
import argparse, importlib.util, json, statistics, time
from pathlib import Path

def load(path, name):
    spec=importlib.util.spec_from_file_location(name, path)
    module=importlib.util.module_from_spec(spec)
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"03-Sources"))
    sys.path.insert(0,str(Path(path).parent))
    spec.loader.exec_module(module)
    return module

def dataset(size):
    return [(f"K-{i:08d}", {"asset_ids":[f"netapp-{i:08d}"],"review_eligibility":"BLOCKED_CONTRADICTION" if i%7==0 else "REVIEW_REQUIRED", "note":f"site {i%17} storage fabric {i%31}"}) for i in range(size)]

def run(old_path, new_path, size=10000, repeats=5):
    old=load(old_path,"governance_old"); new=load(new_path,"governance_new")
    items=dataset(size)
    output=[]
    for query in ("", "status:blocked", "asset:netapp-000099", "site 4", "fabric 12", "key:K-00000099"):
        samples={}
        for label, mod in (("previous",old),("current",new)):
            times=[]; count=None
            for _ in range(repeats):
                start=time.perf_counter(); results=mod.filter_candidates(items,query); times.append((time.perf_counter()-start)*1000)
                keys=[(i,k) for i,k,_ in results]
                if count is None: count=keys
                elif keys!=count: raise AssertionError("Nondeterministic search")
                if label=="current" and keys!=expected: raise AssertionError("Cross-version mismatch")
            if label=="previous": expected=count
            samples[label]={"median_ms":round(statistics.median(times),3),"matches":len(count)}
        output.append({"query":query,**samples,"ratio_current_previous":round(samples["current"]["median_ms"]/max(samples["previous"]["median_ms"],.000001),3)})
    return {"size":size,"repeats":repeats,"measure":"Python filtering only; synthetic data; no GUI","results":output}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--previous",required=True);p.add_argument("--current",required=True);p.add_argument("--size",type=int,default=10000);p.add_argument("--repeats",type=int,default=5);p.add_argument("--output");a=p.parse_args()
    if a.size<1 or a.size>100000 or a.repeats<1 or a.repeats>30: p.error("Invalid size/repeats")
    result=run(a.previous,a.current,a.size,a.repeats)
    payload=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output: Path(a.output).write_text(payload+"\n",encoding="utf-8")
    print(payload)
