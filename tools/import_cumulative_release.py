#!/usr/bin/env python3
"""Import a cumulative StorageScope archive into a clean Git working tree.

Usage: python tools/import_cumulative_release.py /path/to/StorageScope-v6.113-Cumulative.zip
Run from repository root; inspect the diff and run tests before committing.
"""
from __future__ import annotations
import argparse
import pathlib
import subprocess
import sys
import stat
import zipfile
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
TRACKED = ("01-Application", "02-Compilation-Windows", "03-Sources",
           "04-Tests-et-Qualification", "05-Documentation",
           "06-Historique", "07-Manifestes", "binary", ".github")
ROOT_FILES = ("README-DEMARRAGE.md",)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=pathlib.Path)
    parser.add_argument("--max-uncompressed-mib", type=int, default=2048,
                        help="Reject archives larger than this uncompressed size")
    parser.add_argument("--apply", action="store_true",
                        help="Write files; without this flag only show the import plan")
    args = parser.parse_args()
    if subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                      capture_output=True, text=True, check=True).stdout.strip():
        parser.error("Working tree is not clean")
    with zipfile.ZipFile(args.archive) as zf:
        version_paths = ("01-Application/VERSION.txt", "03-Sources/VERSION", "07-Manifestes/VERSION")
        archive_versions = {}
        for version_path in version_paths:
            try:
                value = zf.read(version_path).decode("utf-8-sig").strip()
            except (KeyError, UnicodeError) as exc:
                parser.error(f"Missing or unreadable archive metadata: {version_path}: {exc}")
            if not re.fullmatch(r"\\d+\\.\\d+", value):
                parser.error(f"Invalid archive version in {version_path}: {value!r}")
            archive_versions[version_path] = value
        if len(set(archive_versions.values())) != 1:
            parser.error(f"Archive version drift: {archive_versions}")
        current_version = (ROOT / "07-Manifestes/VERSION").read_text(encoding="utf-8").strip()
        archive_version = next(iter(archive_versions.values()))
        if tuple(map(int, archive_version.split("."))) < tuple(map(int, current_version.split("."))):
            parser.error(f"Archive version {archive_version} is older than repository {current_version}")
        entries = []
        seen = set()
        total_size = 0
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = pathlib.PurePosixPath(info.filename)
            if name.is_absolute() or ".." in name.parts or "\\" in info.filename:
                parser.error(f"Unsafe archive entry: {info.filename}")
            if len(name.parts) < 1 or name == pathlib.PurePosixPath("."):
                continue
            if name.as_posix() in seen:
                parser.error(f"Duplicate archive entry: {info.filename}")
            seen.add(name.as_posix())
            unix_mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(unix_mode):
                parser.error(f"Symbolic links are not allowed: {info.filename}")
            total_size += info.file_size
            if total_size > args.max_uncompressed_mib * 1024 * 1024:
                parser.error("Archive exceeds uncompressed size limit")
            if info.file_size > 1024 * 1024 and info.compress_size and info.file_size / info.compress_size > 500:
                parser.error(f"Suspicious compression ratio: {info.filename}")
            if name.parts[0] == ".github":
                continue  # Preserve CI/security policies maintained in GitHub.
            if name.parts[0] not in TRACKED and str(name) not in ROOT_FILES:
                continue
            # Do not import binary executables into source control.
            if name.parts[0] == "binary" and name.suffix.lower() in (".exe", ".dll", ".msi", ".zip"):
                continue
            entries.append((info, ROOT.joinpath(*name.parts)))
        if not any(p.name == "VERSION" and p.parent.name == "07-Manifestes" for _,p in entries):
            parser.error("Missing release version")
        print(f"Archive: {args.archive}; files selected: {len(entries)}")
        if args.apply:
            for info, dest in entries:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(info))
            print("Imported. Review: git diff --stat; run test suite before commit.")
        else:
            print("Dry run. Use --apply to write files.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
