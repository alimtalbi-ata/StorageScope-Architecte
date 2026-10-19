"""Read-only audit of desktop navigation; author Abdelhalim Talbi."""
from pathlib import Path
import ast
import json
import re
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "03-Sources" / "storagescope_windows.py"
def audit(path=SOURCE):
    source = Path(path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    pages = sorted(set(re.findall(r"navigate_safely\(['\"]([^'\"]+)['\"]\)", source)))
    shortcuts = sorted(set(re.findall(r"root\.bind\(['\"]([^'\"]+)['\"]", source)))
    functions = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    issues = [f"Missing {name} entrypoint" for name in ("main", "launch") if name not in functions]
    duplicates = sorted({key for key in bindings if bindings.count(key) > 1})
    if duplicates: issues.append("Duplicate root bindings: " + ", ".join(duplicates))
    return {"source":str(path),"pages_referenced":pages,"shortcuts":shortcuts,"functions":len(functions),"issues":issues,"method":"static audit, not runtime UI validation"}
if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
