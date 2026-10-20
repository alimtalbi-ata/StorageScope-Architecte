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
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
TRACKED = ("01-Application", "02-Compilation-Windows", "03-Sources",
           "04-Tests-et-Qualification", "05-Documentation",
           "06-Historique", "07-Manifestes", "binary", ".github")
ROOT_FILES = ("README-DEMARRAGE.md",)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=pathlib.Path)
    parser.add_argument("--apply", action="store_true",
                        help="Write files; without this flag only show the import plan")
    args = parser.parse_args()
    if subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                      capture_output=True, text=True, check=True).stdout.strip():
        parser.error("Working tree is not clean")
    with zipfile.ZipFile(args.archive) as zf:
        entries = []
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = pathlib.PurePosixPath(info.filename)
            if name.is_absolute() or ".." in name.parts or "\\" in info.filename:
                parser.error(f"Unsafe archive entry: {info.filename}")
            if len(name.parts) < 1:
                continue
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
