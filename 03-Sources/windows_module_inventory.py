"""Deterministic local import graph for the Windows entrypoint. Author: Abdelhalim Talbi."""
import ast
from pathlib import Path


def reachable_modules(root, entry='storagescope_windows'):
    root = Path(root)
    modules = {p.stem: p for p in root.glob('*.py') if not p.stem.startswith('test_')}
    if entry not in modules:
        raise ValueError('Entry module absent')
    visited, pending = set(), [entry]
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        tree = ast.parse(modules[name].read_text(encoding='utf-8'), filename=str(modules[name]))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports = [alias.name.split('.')[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imports = [node.module.split('.')[0]]
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == '__import__' and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                imports = [node.args[0].value.split('.')[0]]
            else:
                continue
            pending.extend(sorted(i for i in imports if i in modules and i not in visited))
    return sorted(visited - {entry})


if __name__ == '__main__':
    print('\n'.join(reachable_modules(Path(__file__).resolve().parent)))
