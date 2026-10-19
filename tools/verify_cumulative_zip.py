"""Fail-closed cumulative archive integrity and version audit.

Author: Abdelhalim Talbi.
Usage: python tools/verify_cumulative_zip.py release.zip --version 6.117
"""
import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import PurePosixPath

VERSIONS = ("01-Application/VERSION.txt", "03-Sources/VERSION", "07-Manifestes/VERSION")

def verify(path, expected=None):
    errors = []
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        names = [m.filename for m in members if not m.is_dir()]
        if len(members) > 10000:
            errors.append("Archive exceeds safe member limit")
        total_size = sum(m.file_size for m in members)
        if total_size > 2 * 1024 * 1024 * 1024:
            errors.append("Archive exceeds safe uncompressed size limit")
        if len(names) != len(set(names)):
            errors.append("Duplicate ZIP members")
        for member in members:
            p = PurePosixPath(member.filename)
            if p.is_absolute() or ".." in p.parts or "\\" in member.filename:
                errors.append("Unsafe archive path: " + member.filename)
            if (member.external_attr >> 16) & 0o170000 == 0o120000:
                errors.append("Symlink archive member: " + member.filename)
        # Never decompress an archive whose metadata already violates limits.
        if errors:
            return {"ok": False, "version": None, "files": len(names), "errors": errors}
        if archive.testzip() is not None:
            errors.append("Corrupted ZIP member")
        values = {}
        for name in VERSIONS:
            if name not in names:
                errors.append("Missing version: " + name)
                continue
            try:
                values[name] = archive.read(name).decode("utf-8").strip()
            except UnicodeDecodeError:
                errors.append("Invalid UTF-8 version: " + name)
        if len(set(values.values())) > 1:
            errors.append("Version mismatch: " + str(values))
        version = next(iter(values.values()), None)
        if expected and version != expected:
            errors.append(f"Expected {expected}, found {version}")
        manifest_name = f"07-Manifestes/SHA256-v{version}.json"
        if manifest_name in names:
            try:
                manifest = json.loads(archive.read(manifest_name))
            except (ValueError, UnicodeDecodeError) as exc:
                errors.append("Invalid SHA256 manifest: " + str(exc))
                manifest = {}
            if not isinstance(manifest, dict):
                errors.append("SHA256 manifest must be an object")
                manifest = {}
            for name, digest in manifest.items():
                if not isinstance(name, str) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                    errors.append("Invalid SHA256 manifest entry: " + str(name))
                    continue
                if name not in names:
                    errors.append("Missing manifest member: " + name)
                elif hashlib.sha256(archive.read(name)).hexdigest() != digest:
                    errors.append("SHA256 mismatch: " + name)
            missing = set(names) - set(manifest) - {manifest_name}
            if missing:
                errors.append("Unmanifested files: " + ", ".join(sorted(missing)[:10]))
        else:
            errors.append("Missing SHA256 manifest: " + manifest_name)
    return {"ok": not errors, "version": version, "files": len(names), "errors": errors}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive")
    parser.add_argument("--version")
    args = parser.parse_args()
    result = verify(args.archive, args.version)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["ok"] else 2)
