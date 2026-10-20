"""Read-only risk review of candidate inventory matches.

Author: Abdelhalim Talbi.
"""
from inventory_reconcile_v619 import reconcile, IDENTITY_FIELDS

def review_inventory(records):
    report = reconcile(records)
    for candidate in report["candidates"]:
        left, right = (records[index] for index in candidate["indices"])
        mismatches = []
        for field in IDENTITY_FIELDS:
            a, b = left.get(field), right.get(field)
            if isinstance(a, str) and isinstance(b, str) and a.strip() and b.strip():
                if a.strip().casefold() != b.strip().casefold():
                    mismatches.append(field)
        same_source = left.get("source") == right.get("source")
        candidate["identity_disagreements"] = mismatches
        candidate["same_source"] = same_source
        candidate["risk"] = ("HIGH" if mismatches else
                             "MEDIUM" if same_source or candidate["conflicts"] else "LOW")
        candidate["review_required"] = True
    report["high_risk_count"] = sum(item["risk"] == "HIGH" for item in report["candidates"])
    return report
