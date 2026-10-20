"""Static inventory of component dependencies, with an auditable JSON report.

Author: Abdelhalim Talbi. This is static analysis, not a runtime usage metric.
"""
import argparse
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "03-Sources"

def inventory(source=SOURCE):
    source = Path(source)
    files = sorted(source.rglob("*.py"))
    modules = {p.stem for p in files if p.name != "__init__.py"}
    rows = []
    for path in files:
        rel = path.relative_to(source).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = set()
        functions = 0
        classes = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions += 1
            elif isinstance(node, ast.ClassDef):
                classes += 1
        rows.append({"path": rel, "imports_internal": sorted(imports & modules),
                     "functions": functions, "classes": classes, "bytes": path.stat().st_size})
    referenced = {name for row in rows for name in row["imports_internal"]}
    candidates = sorted(p for p in modules - referenced if p not in {"storagescope_windows", "__main__"})
    return {"source_files": len(files), "components": rows,
            "potentially_unreferenced_modules": candidates,
            "warning": "Potentially unreferenced does not mean unused: dynamic imports, plugins, scripts and entrypoints are not captured."}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(SOURCE))
    parser.add_argument("--output")
    args = parser.parse_args()
    report = inventory(args.source)
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
    else:
        print(content)
