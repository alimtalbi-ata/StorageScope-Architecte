"""StorageScope v6.18: read-only inventory quality inspection. No destructive merge."""
from __future__ import annotations
import argparse, collections, datetime as dt, json, pathlib

REQUIRED=("id","name","type")
def inspect_inventory(items, now=None, max_age_days=90):
    if not isinstance(items,list): raise ValueError("Inventory must be a JSON array")
    now=now or dt.datetime.now(dt.timezone.utc)
    issues=[]; seen={}
    for index,item in enumerate(items):
        if not isinstance(item,dict):
            issues.append({"index":index,"code":"invalid_record","detail":"Expected object"});continue
        for key in REQUIRED:
            if not isinstance(item.get(key),str) or not item[key].strip():
                issues.append({"index":index,"code":"missing_field","field":key})
        ident=item.get("id")
        if isinstance(ident,str) and ident.strip():
            ident=ident.strip()
            if ident in seen:issues.append({"index":index,"code":"duplicate_id","id":ident,"first_index":seen[ident]})
            else:seen[ident]=index
        stamp=item.get("updated_at")
        if stamp is not None:
            try:
                if not isinstance(stamp,str):raise ValueError("not a string")
                value=dt.datetime.fromisoformat(stamp.replace("Z","+00:00"))
                if value.tzinfo is None:raise ValueError("timezone required")
                age=(now-value.astimezone(dt.timezone.utc)).total_seconds()/86400
                if age < -1/86400:issues.append({"index":index,"code":"future_timestamp"})
                elif age>max_age_days:issues.append({"index":index,"code":"stale_record","age_days":round(age,2)})
            except (ValueError,OverflowError):issues.append({"index":index,"code":"invalid_timestamp"})
    by_code=dict(sorted(collections.Counter(x["code"] for x in issues).items()))
    return {"schema":"storagescope.inventory-quality.v1","total":len(items),"issue_count":len(issues),"score":round(max(0,100*(1-len(issues)/max(1,len(items)*5))),2),"counts":by_code,"issues":issues,"destructive_changes":0}

def main(argv=None):
    p=argparse.ArgumentParser(description="Read-only CMDB inventory quality check")
    p.add_argument("input",type=pathlib.Path);p.add_argument("--output",type=pathlib.Path);p.add_argument("--max-age-days",type=int,default=90)
    a=p.parse_args(argv)
    if a.max_age_days<0:p.error("max age must be non-negative")
    result=inspect_inventory(json.loads(a.input.read_text(encoding="utf-8")),max_age_days=a.max_age_days)
    payload=json.dumps(result,indent=2,ensure_ascii=False)
    if a.output:a.output.write_text(payload+"\n",encoding="utf-8")
    else:print(payload)
    return 0 if not result["issue_count"] else 1
if __name__=="__main__":raise SystemExit(main())
