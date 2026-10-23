#!/usr/bin/env python3
"""Isolated, fail-closed historical regression runner for StorageScope Windows.

Keeps test-relative fixtures, imports application modules, checks executed counts,
and writes evidence even on failing assertions. No test is skipped or mocked.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

COUNT = re.compile(r"\bRan\s+(\d+)\s+tests?\s+in\b")
CASE = re.compile(r"^(ERROR|FAIL):\s+(.+)$", re.MULTILINE)
# The two files have distinct purposes; source variant is for legacy tests.
KNOWN_DIFFERENT_FILES = {"verify-windows-build.py"}


def classify(output: str) -> dict[str, int]:
    markers = list(CASE.finditer(output))
    result = Counter()
    for i, match in enumerate(markers):
        block = output[match.start():markers[i + 1].start() if i + 1 < len(markers) else len(output)]
        if "WinError 32" in block or "database is locked" in block or "PermissionError" in block:
            cause = "windows_lock_or_permission"
        elif "ModuleNotFoundError" in block or "ImportError" in block:
            cause = "import_or_dependency"
        elif "FileNotFoundError" in block or "NotADirectoryError" in block:
            cause = "path_or_fixture"
        elif "UnicodeDecodeError" in block or "UnicodeEncodeError" in block:
            cause = "encoding"
        elif "sqlite3." in block:
            cause = "sqlite_other"
        elif match.group(1) == "FAIL":
            cause = "assertion_failure"
        else:
            cause = "other_error"
        result[cause] += 1
    return dict(sorted(result.items()))


def run_suite(start: Path, pattern: str, root: Path, env: dict[str, str],
              minimum: int, label: str) -> dict:
    command = [sys.executable, "-B", "-m", "unittest", "discover",
               "-s", str(start), "-p", pattern, "-q"]
    completed = subprocess.run(command, cwd=root, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, encoding="utf-8",
                               errors="replace", check=False)
    print(f"===== {label} =====\n{completed.stdout}", flush=True)
    counts = COUNT.findall(completed.stdout)
    executed = int(counts[-1]) if counts else None
    ok = completed.returncode == 0 and executed is not None and executed >= minimum
    return {"suite": label, "executed": executed, "minimum": minimum,
            "exit_code": completed.returncode, "status": "PASS" if ok else "FAIL",
            "symptom_counts": classify(completed.stdout)}


def execute(repo: Path, minimum_tests: int = 958, minimum_nested: int = 8,
            report: Path | None = None) -> dict:
    if minimum_tests < 1 or minimum_nested < 0:
        raise ValueError("Invalid minimum test count")
    if not (repo / "03-Sources").is_dir() or not (repo / "04-Tests-et-Qualification").is_dir():
        raise FileNotFoundError("StorageScope source/test directories are missing")
    with tempfile.TemporaryDirectory(prefix="storagescope-regression-") as temp:
        checkout = Path(temp) / "checkout"
        shutil.copytree(repo, checkout, ignore=shutil.ignore_patterns(
            ".git", "__pycache__", ".venv", ".build-venv", ".build-stage",
            ".pytest_cache", ".publish-pending", ".publish-backup",
            "build-logs", "failed-build-logs", "dist", ".binary-staging"))
        sources = checkout / "03-Sources"
        build = checkout / "02-Compilation-Windows"
        tests = checkout / "04-Tests-et-Qualification"
        nested_files = sorted(p for p in tests.rglob("test_*.py") if p.parent != tests)
        if not list(tests.glob("test_*.py")):
            raise RuntimeError("No top-level historical tests discovered")
        # Some historical tests require colocated modules and fixtures.
        # Preserve the original tests directory; never overwrite test assets.
        for source in sorted(sources.glob("*.py")) + sorted(build.iterdir()):
            if not source.is_file() or source.name.startswith("test_"):
                continue
            target = tests / source.name
            if target.exists():
                if target.read_bytes() != source.read_bytes():
                    if source.parent == build and source.name in KNOWN_DIFFERENT_FILES:
                        continue
                    raise RuntimeError("Unreviewed fixture collision: " + source.name)
                continue
            shutil.copy2(source, target)
        if (checkout / ".github").is_dir():
            shutil.copytree(checkout / ".github", tests / ".github", dirs_exist_ok=True)
        version = checkout / "07-Manifestes" / "VERSION"
        if version.is_file():
            dest = tests / "VERSION"
            if dest.exists() and dest.read_bytes() != version.read_bytes():
                raise RuntimeError("VERSION collision")
            if not dest.exists():
                shutil.copy2(version, dest)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONPATH"] = os.pathsep.join(filter(None, [
            str(tests), str(sources), str(checkout), env.get("PYTHONPATH")]))
        rows = [run_suite(tests, "test_*.py", checkout, env, minimum_tests, "historical")]
        for nested in nested_files:
            rows.append(run_suite(nested.parent, nested.name, checkout, env, 1,
                                  nested.relative_to(tests).as_posix()))
    nested_count = sum(r["executed"] or 0 for r in rows[1:])
    passed = all(r["status"] == "PASS" for r in rows) and nested_count >= minimum_nested
    data = {"status": "PASS" if passed else "FAIL",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "main_minimum": minimum_tests, "nested_minimum": minimum_nested,
            "nested_executed": nested_count, "suites": rows,
            "evidence": "actual_unittest_subprocesses",
            "qualification": "tests_only_not_windows_binary"}
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
        pending = report.with_name(report.name + ".tmp")
        pending.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        pending.replace(report)
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--minimum-tests", type=int, default=958)
    parser.add_argument("--minimum-nested-tests", type=int, default=8)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        result = execute(args.repo.resolve(), args.minimum_tests,
                         args.minimum_nested_tests, args.report)
        print("HISTORICAL_SUITE_RESULT: " + result["status"])
        return 0 if result["status"] == "PASS" else 1
    except Exception as exc:
        failure = {"status": "FAIL", "error_type": type(exc).__name__,
                   "error": str(exc), "qualification": "tests_only_not_windows_binary"}
        if args.report:
            try:
                args.report.parent.mkdir(parents=True, exist_ok=True)
                pending = args.report.with_name(args.report.name + ".tmp")
                pending.write_text(json.dumps(failure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                pending.replace(args.report)
            except OSError as evidence_error:
                print(f"HISTORICAL_SUITE_REPORT_ERROR: {evidence_error}", file=sys.stderr)
        print(f"HISTORICAL_SUITE_FATAL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
