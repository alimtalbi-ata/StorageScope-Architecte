"""Read-only governance integration service v6.27. No automatic merge."""
from __future__ import annotations
import copy
from governance_core import inspect
from identity_policy import analyze

def assess(records):
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    data = copy.deepcopy(records)
    report = inspect(data)
    identity = analyze(data)
    blocked = {tuple(c["indices"]) for c in identity["candidates"] if c["status"] == "BLOCKED_CONTRADICTION"}
    for candidate in report["reconciliation"]["candidates"]:
        indices = tuple(sorted(candidate["indices"]))
        if indices in blocked:
            candidate["review_eligibility"] = "BLOCKED_CONTRADICTION"
            candidate["review_key"] = None
            candidate["action"] = "BLOCKED"
    report["review_eligible"] = sum(bool(c.get("review_key")) for c in report["reconciliation"]["candidates"])
    report["identity_policy"] = identity
    report["schema"] = "storagescope.governance.v3"
    report["automatic_merges"] = 0
    return report
