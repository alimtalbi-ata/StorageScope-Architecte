"""Conservative architecture risk report from the component inventory.

Author: Abdelhalim Talbi. Findings are review candidates, not deletion advice.
"""
import argparse
import json
from pathlib import Path

def review(inventory):
    components = inventory["components"]
    inbound = {}
    for item in components:
        for dependency in item["imports_internal"]:
            inbound[dependency] = inbound.get(dependency, 0) + 1
    rows = []
    for item in components:
        name = Path(item["path"]).stem
        score = 0
        reasons = []
        if item["bytes"] >= 100_000:
            score += 2
            reasons.append("Large module: consider separation of UI, services and persistence")
        if item["functions"] >= 50:
            score += 2
            reasons.append("Many functions: inspect cohesion and test boundaries")
        if inbound.get(name, 0) >= 8:
            score += 1
            reasons.append("High dependency fan-in: changes need broader regression")
        if name in inventory["potentially_unreferenced_modules"]:
            reasons.append("No static inbound imports; verify entrypoints and dynamic usage")
        if reasons:
            rows.append({"module": item["path"], "risk_score": score,
                         "static_inbound": inbound.get(name, 0), "review_reasons": reasons})
    rows.sort(key=lambda x: (-x["risk_score"], x["module"]))
    return {"review_candidates": rows, "module_count": len(components),
            "interpretation": "Static heuristics only; verify runtime use and UI workflows before refactoring."}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = review(json.loads(Path(args.inventory).read_text(encoding="utf-8")))
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output: Path(args.output).write_text(output, encoding="utf-8")
    else: print(output)
