"""Audit desktop navigation and key bindings without executing Tk.

Author: Abdelhalim Talbi. Static evidence is not a GUI interaction test.
"""
from pathlib import Path
import ast
import json
import re
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "03-Sources" / "storagescope_windows.py"

def audit(path=SOURCE):
    source = Path(path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    pages = sorted(set(re.findall('navigate_safely\\\\([\\\'\"]([^\\\'\"]+)[\\\'\"]\\\\)', source)))
    bindings = re.findall('root\\\\.bind\\\\([\\\'\"]([^\\\'\"]+)[\\\'\"]', source)
    shortcuts = sorted(set(bindings))
    functions = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    issues = [f"Missing {name} entrypoint" for name in ("main", "launch") if name not in functions]
    duplicates = sorted({key for key in bindings if bindings.count(key) > 1})
    if duplicates:
        issues.append("Duplicate root bindings: " + ", ".join(duplicates))
    # Multiple widget bindings to the same key are legitimate; this check only
    # audits repeated root-level registrations visible in source.
    return {"source": str(path), "pages_referenced": pages, "shortcuts": shortcuts,
            "functions": len(functions), "issues": issues,
            "method": "static audit, not runtime UI validation"}
if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
