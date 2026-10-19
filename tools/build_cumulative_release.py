"""Build a reproducible cumulative ZIP from a single checked-out commit.

Author: Abdelhalim Talbi. The source tree is never mutated.
Only run after the native Windows qualification gate has passed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
VERSIONS = ("01-Application/VERSION.txt", "03-Sources/VERSION", "07-Manifestes/VERSION")

def build(root, output, *, require_windows=True):
    root, output = Path(root).resolve(), Path(output).resolve()
    version_values = {(root / p).read_text(encoding="utf-8").strip() for p in VERSIONS}
    if len(version_values) != 1:
        raise ValueError("Release versions disagree")
    version = version_values.pop()
    if require_windows:
        evidence = root / "02-Compilation-Windows/windows-release-qualification.json"
        report = json.loads(evidence.read_text(encoding="utf-8"))
        if report.get("status") != "PASS":
            raise ValueError("Windows qualification gate is not PASS")
        binary_dir = root / "binary" / ("v" + version)
        if not binary_dir.is_dir():
            raise ValueError("Qualified Windows binaries missing")
        for name in ("StorageScope.exe", f"StorageScope-Setup-v{version}.exe", f"StorageScope-Portable-v{version}-win-x64.zip"):
            if not (binary_dir / name).is_file():
                raise ValueError("Missing qualified Windows deliverable: " + name)
    files = {}
    for file in root.rglob("*"):
        if not file.is_file() or file.is_symlink():
            continue
        relative = file.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in relative.parts) or file.suffix in EXCLUDED_SUFFIXES:
            continue
        if file.resolve() == output:
            continue
        name = relative.as_posix()
        if name.startswith("07-Manifestes/SHA256-v"):
            continue
        files[name] = file
    manifest_path = f"07-Manifestes/SHA256-v{version}.json"
    manifest = {name: hashlib.sha256(file.read_bytes()).hexdigest() for name, file in sorted(files.items())}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".zip", delete=False) as tmp:
        temporary = Path(tmp.name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
            for name, file in sorted(files.items()):
                archive.write(file, name)
            archive.writestr(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise ValueError("ZIP integrity failure")
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return {"version": version, "files": len(files) + 1, "archive": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-only", action="store_true", help="Explicitly build an unqualified source candidate")
    args = parser.parse_args()
    print(json.dumps(build(args.root, args.output, require_windows=not args.source_only), indent=2))
