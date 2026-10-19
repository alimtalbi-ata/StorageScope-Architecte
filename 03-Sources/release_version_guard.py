"""Fail CI when Windows release metadata disagree with the packaged sources.

This intentionally checks the *current repository* version, not the separately
distributed cumulative preview archive. Author: Abdelhalim Talbi.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FILES = ("01-Application/VERSION.txt", "03-Sources/VERSION", "07-Manifestes/VERSION")

def check_release_versions(root=ROOT):
    versions = {}
    for name in FILES:
        value = (root / name).read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"\d+\.\d+", value):
            raise ValueError(f"Invalid version in {name}: {value!r}")
        versions[name] = value
    script = (root / "02-Compilation-Windows/StorageScope.iss").read_text(encoding="utf-8")
    match = re.search(r'^#define AppVersion "(\d+\.\d+)"$', script, re.MULTILINE)
    if not match:
        raise ValueError("Missing Inno Setup AppVersion")
    versions["Inno Setup AppVersion"] = match.group(1)
    entrypoint = (root / "03-Sources/storagescope_windows.py").read_text(encoding="utf-8")
    entry_version = re.search(r"""^VERSION\s*=\s*['"](\d+\.\d+)['"]""", entrypoint, re.MULTILINE)
    if not entry_version:
        raise ValueError("Missing Windows application VERSION")
    versions["Windows application VERSION"] = entry_version.group(1)
    if len(set(versions.values())) != 1:
        raise ValueError(f"Version drift detected: {versions}")
    return next(iter(versions.values()))

if __name__ == "__main__":
    print("PASS release metadata:", check_release_versions())
