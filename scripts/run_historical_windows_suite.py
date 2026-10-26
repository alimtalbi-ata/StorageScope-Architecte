#!/usr/bin/env python3
"""Isolated, fail-closed historical regression runner for StorageScope Windows.

Keeps test-relative fixtures, imports application modules, checks executed counts,
and writes evidence even on failing assertions. No test is skipped or mocked.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import argparse
import hashlib
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
import uuid

# Resolve the repository root when this script is invoked by absolute path.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from tools.strict_subprocess_output import decode_subprocess_output

COUNT = re.compile(r"\bRan\s+(\d+)\s+tests?\s+in\b")
CASE = re.compile(r"^(ERROR|FAIL):\s+(.+)$", re.MULTILINE)
RESULT_SUMMARY = re.compile(r"^(?P<status>OK|FAILED)(?:\s*\((?P<details>[^()]*)\))?\s*$")
RUNNER_RESULT_PREFIX = "STORAGESCOPE_UNITTEST_RESULT:"
SUMMARY_DETAIL = re.compile(r"^(?P<name>skipped|expected failures|failures|errors|unexpected successes)\s*=\s*(?P<count>\d+)$")
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



def parse_terminal_summary(output: str, expected_token: str | None = None) -> dict:
    """Parse the authoritative unittest result marker, with a legacy log fallback."""
    lines = output.splitlines()
    observed_marker_indexes = [i for i, line in enumerate(lines)
                               if line.startswith(RUNNER_RESULT_PREFIX)]

    if expected_token is not None:
        # Bind the marker to this invocation: nested tests can launch their own
        # runner and emit diagnostic markers inside the parent's captured output.
        expected_prefix = f"{RUNNER_RESULT_PREFIX}{expected_token}: "
        marker_indexes = [i for i, line in enumerate(lines)
                          if line.startswith(expected_prefix)]
        if not marker_indexes:
            problems = ["authoritative runner result marker for this invocation missing"]
            if observed_marker_indexes:
                problems.append("only nested/foreign runner result markers were observed")
            return {
                "status": "UNKNOWN", "summary_line": None, "tests_run": None,
                "failures": 0, "errors": 0, "skipped": 0,
                "expected_failures": 0, "unexpected_successes": 0,
                "summary_complete": False, "trailing_output_lines": 0,
                "problems": problems, "summary_source": "runner_result_marker",
            }
    elif observed_marker_indexes:
        return {
            "status": "UNKNOWN", "summary_line": None, "tests_run": None,
            "failures": 0, "errors": 0, "skipped": 0,
            "expected_failures": 0, "unexpected_successes": 0,
            "summary_complete": False, "trailing_output_lines": 0,
            "problems": ["result marker token is required to disambiguate nested invocations"],
            "summary_source": "runner_result_marker",
        }
    else:
        expected_prefix = ""
        marker_indexes = []

    if marker_indexes:
        problems = []
        if len(marker_indexes) != 1:
            problems.append("expected exactly one runner result marker for this invocation")
        marker_index = marker_indexes[-1]
        trailing = sum(bool(line.strip()) for line in lines[marker_index + 1:])
        if trailing:
            problems.append("non-empty output follows runner result marker")
        try:
            payload = json.loads(lines[marker_index][len(expected_prefix):])
            status = payload.get("status")
            tests_run = payload.get("tests_run")
            numeric_fields = ("failures", "errors", "skipped",
                              "expected_failures", "unexpected_successes")
            required_fields = {"status", "tests_run", *numeric_fields}
            missing_fields = sorted(required_fields - set(payload))
            if missing_fields:
                problems.append("runner result marker missing required fields: " + ", ".join(missing_fields))
            if status not in {"OK", "FAILED"}:
                problems.append("runner result marker has unsupported status")
            if not isinstance(tests_run, int) or isinstance(tests_run, bool) or tests_run < 0:
                problems.append("runner result marker has invalid tests_run")
            counts = {}
            for field in numeric_fields:
                value = payload.get(field)
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    problems.append("runner result marker has invalid " + field)
                else:
                    counts[field] = value
            if status == "OK" and any(counts.get(field, 0) for field in
                                      ("failures", "errors", "unexpected_successes")):
                problems.append("OK runner result marker contains failing counts")
            if status == "FAILED" and not any(counts.get(field, 0) for field in
                                               ("failures", "errors", "unexpected_successes")):
                problems.append("FAILED runner result marker declares no failure")
            valid_tests = tests_run if isinstance(tests_run, int) and not isinstance(tests_run, bool) else None
            return {
                "status": status if status in {"OK", "FAILED"} else "UNKNOWN",
                "summary_line": lines[marker_index],
                "tests_run": valid_tests,
                "failures": counts.get("failures", 0),
                "errors": counts.get("errors", 0),
                "skipped": counts.get("skipped", 0),
                "expected_failures": counts.get("expected_failures", 0),
                "unexpected_successes": counts.get("unexpected_successes", 0),
                "summary_complete": not problems and valid_tests is not None,
                "trailing_output_lines": trailing,
                "problems": problems,
                "summary_source": "runner_result_marker",
            }
        except (json.JSONDecodeError, AttributeError, TypeError) as exc:
            problems.append("invalid runner result marker: " + str(exc))
            return {
                "status": "UNKNOWN", "summary_line": lines[marker_index],
                "tests_run": None, "failures": 0, "errors": 0, "skipped": 0,
                "expected_failures": 0, "unexpected_successes": 0,
                "summary_complete": False, "trailing_output_lines": trailing,
                "problems": problems, "summary_source": "runner_result_marker",
            }

    result_positions = []
    for index, raw in enumerate(lines):
        match = RESULT_SUMMARY.fullmatch(raw.strip())
        if match:
            result_positions.append((index, match))
    counts = list(COUNT.finditer(output))
    base = {
        "status": "UNKNOWN",
        "summary_line": None,
        "tests_run": int(counts[-1].group(1)) if counts else None,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "expected_failures": 0,
        "unexpected_successes": 0,
        "summary_complete": False,
        "trailing_output_lines": 0,
        "problems": [],
        "summary_source": "text_fallback",
    }
    if not result_positions:
        base["problems"].append("terminal unittest result summary missing")
        return base

    index, match = result_positions[-1]
    line = lines[index].strip()
    base["status"] = match.group("status")
    base["summary_line"] = line
    base["trailing_output_lines"] = sum(bool(x.strip()) for x in lines[index + 1:])
    final_count_end = counts[-1].end() if counts else None
    line_start = sum(len(x) + 1 for x in lines[:index])
    if final_count_end is None:
        base["problems"].append("test-count summary missing")
    elif final_count_end > line_start:
        base["problems"].append("terminal result summary precedes the final test-count summary")

    details = match.group("details") or ""
    allowed = {
        "OK": {"skipped", "expected failures"},
        "FAILED": {"failures", "errors", "skipped", "expected failures", "unexpected successes"},
    }[base["status"]]
    seen = set()
    if details:
        for part in details.split(","):
            field = SUMMARY_DETAIL.fullmatch(part.strip())
            if not field:
                base["problems"].append("unparseable terminal unittest summary detail")
                continue
            name = field.group("name")
            if name not in allowed:
                base["problems"].append("unsupported terminal unittest summary field: " + name)
                continue
            if name in seen:
                base["problems"].append("duplicate terminal unittest summary field: " + name)
                continue
            seen.add(name)
            key = {"expected failures": "expected_failures", "unexpected successes": "unexpected_successes"}.get(name, name)
            base[key] = int(field.group("count"))

    if base["status"] == "FAILED" and not (
        base["failures"] + base["errors"] + base["unexpected_successes"]
    ):
        base["problems"].append("FAILED terminal summary declares no failure, error, or unexpected success")
    if base["trailing_output_lines"]:
        base["problems"].append("non-empty output follows terminal unittest result summary")
    base["summary_complete"] = not base["problems"] and base["tests_run"] is not None
    return base


def _stage_workflow_fixture_file(source: Path, target: Path, relative_name: str) -> None:
    """Copy one fixture without overwriting a destination, including races."""
    if source.is_symlink():
        raise RuntimeError("Refusing symlink in workflow source tree: " + relative_name)
    if not source.is_file():
        raise RuntimeError("Unsupported workflow source entry: " + relative_name)

    source_bytes = source.read_bytes()
    if target.is_symlink():
        raise RuntimeError("Workflow fixture symlink collision: " + relative_name)
    if target.exists():
        if not target.is_file():
            raise RuntimeError("Workflow fixture file/directory collision: " + relative_name)
        if target.read_bytes() != source_bytes:
            raise RuntimeError(
                "Workflow fixture collision; existing test asset preserved: " + relative_name
            )
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        raise RuntimeError("Workflow fixture appeared during staging: " + relative_name)

    pending = target.with_name(target.name + ".staging-" + uuid.uuid4().hex)
    try:
        shutil.copy2(source, pending)
        if pending.read_bytes() != source_bytes:
            raise RuntimeError("Staged workflow bytes failed verification: " + relative_name)
        if target.exists() or target.is_symlink():
            raise RuntimeError("Workflow fixture appeared before atomic promotion: " + relative_name)
        # Hard-link creation is atomic and does not replace an existing path.
        # os.rename/Path.replace could overwrite a concurrently created fixture.
        try:
            os.link(pending, target)
        except FileExistsError as exc:
            raise RuntimeError(
                "Workflow fixture appeared before no-overwrite promotion: " + relative_name
            ) from exc
        pending.unlink()
    finally:
        if pending.exists() or pending.is_symlink():
            pending.unlink()


def stage_workflow_fixtures(source_root: Path, target_root: Path) -> None:
    """Stage workflow fixtures without overwriting assets or traversing nested roots.

    Missing source trees remain a no-op for synthetic checkouts, but a broken
    symlink is an invalid source and must not be mistaken for a missing tree.
    Source and destination roots must be disjoint after path resolution.
    """
    if source_root.is_symlink():
        raise RuntimeError("Workflow source is a symbolic link: " + str(source_root))
    if not source_root.exists():
        return
    if not source_root.is_dir():
        raise RuntimeError("Workflow source is not a regular directory: " + str(source_root))
    if target_root.is_symlink() or (target_root.exists() and not target_root.is_dir()):
        raise RuntimeError("Workflow fixture target is not a regular directory: " + str(target_root))

    try:
        source_resolved = source_root.resolve(strict=True)
        target_resolved = target_root.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise RuntimeError("Unable to resolve workflow fixture roots safely") from exc
    if (
        source_resolved == target_resolved
        or source_resolved in target_resolved.parents
        or target_resolved in source_resolved.parents
    ):
        raise RuntimeError(
            "Workflow source and fixture target trees must be disjoint: "
            + str(source_resolved) + " <> " + str(target_resolved)
        )

    target_root.mkdir(parents=True, exist_ok=True)
    for source in sorted(source_root.rglob("*")):
        relative = source.relative_to(source_root)
        target = target_root / relative
        relative_name = relative.as_posix()
        if source.is_symlink():
            raise RuntimeError("Refusing symlink in workflow source tree: " + relative_name)

        # Validate each destination parent before mkdir/read/write; a fixture
        # directory must not redirect staging through a symlink.
        current = target_root
        for component in relative.parts[:-1]:
            current = current / component
            if current.is_symlink() or (current.exists() and not current.is_dir()):
                raise RuntimeError("Workflow fixture parent collision: " + relative_name)

        if source.is_dir():
            if target.is_symlink() or (target.exists() and not target.is_dir()):
                raise RuntimeError("Workflow fixture directory collision: " + relative_name)
            target.mkdir(parents=True, exist_ok=True)
            continue
        _stage_workflow_fixture_file(source, target, relative_name)


def stage_historical_upgrade_workflow(sources: Path, tests: Path) -> None:
    """Restore the archived v5.89 workflow as a safely staged fixture, not live CI."""
    archived = sources / "Ressources" / ".github" / "workflows" / "windows-upgrade-e2e.yml"
    if archived.is_symlink():
        raise RuntimeError("Refusing symlink as historical workflow source: " + str(archived))
    if not archived.is_file():
        # Minimal/synthetic checkouts do not carry the historical v5.89 test.
        # Fail closed only when that test actually requires this fixture.
        if (tests / "test_windows_portable_v589.py").is_file():
            raise FileNotFoundError("Missing archived Windows upgrade workflow fixture: " + str(archived))
        return

    target_root = tests / ".github" / "workflows"
    for parent in (tests / ".github", target_root):
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            raise RuntimeError("Historical workflow fixture parent is not a regular directory: " + str(parent))
    target_root.mkdir(parents=True, exist_ok=True)
    target = target_root / archived.name
    _stage_workflow_fixture_file(archived, target, archived.name)


def run_suite(start: Path, pattern: str, root: Path, env: dict[str, str],
              minimum: int, label: str, evidence_dir: Path | None = None) -> dict:
    discovery_runner = root / "scripts" / "unittest_discover_with_result.py"
    if not discovery_runner.is_file():
        raise FileNotFoundError("Authoritative unittest discovery runner is missing: " + str(discovery_runner))
    result_token = uuid.uuid4().hex
    command = [sys.executable, "-B", str(discovery_runner),
               "--start", str(start), "--pattern", pattern,
               "--result-token", result_token]
    # Capture bytes, not decoded text: evidence is saved exactly as received,
    # before the strict decoder is allowed to interpret it.
    completed = subprocess.run(command, cwd=root, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, check=False)
    raw_output = completed.stdout
    if not isinstance(raw_output, bytes):
        raise TypeError("subprocess output capture did not return raw bytes")
    raw_sha256 = hashlib.sha256(raw_output).hexdigest()

    log_evidence = {}
    if evidence_dir is not None:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        safe_label = re.sub(r"[^A-Za-z0-9._-]+", "_", label).strip("._") or "suite"
        log_name = f"historical-suite-{safe_label}.log"
        log_path = evidence_dir / log_name
        pending = log_path.with_name(log_path.name + ".tmp")
        pending.write_bytes(raw_output)
        pending.replace(log_path)
        log_evidence = {
            "log_file": log_name,
            "log_sha256": raw_sha256,
            "log_bytes": len(raw_output),
            "log_encoding": "raw_subprocess_bytes",
        }

    try:
        output, decode_provenance = decode_subprocess_output(raw_output)
    except (ValueError, TypeError) as exc:
        problem = str(exc)
        print(
            f"===== {label} =====\n"
            f"HISTORICAL_SUBPROCESS_OUTPUT_REJECTED: {problem}; "
            f"raw_sha256={raw_sha256}; raw_bytes={len(raw_output)}",
            flush=True,
        )
        terminal = {
            "status": "UNKNOWN",
            "summary_line": None,
            "tests_run": None,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "expected_failures": 0,
            "unexpected_successes": 0,
            "summary_complete": False,
            "trailing_output_lines": 0,
            "problems": [
                "subprocess output decoding rejected: " + problem,
                "result was not parsed as text",
            ],
            "summary_source": "strict_utf8_subprocess",
        }
        return {
            "suite": label,
            "executed": None,
            "minimum": minimum,
            "exit_code": completed.returncode,
            "status": "FAIL",
            "terminal_unittest_summary": terminal,
            "symptom_counts": {},
            "captured_output_symptom_counts": {},
            "symptom_counts_scope": (
                "not classified because strict UTF-8 decoding was rejected"
            ),
            "subprocess_output_decoding": {
                "status": "REJECTED",
                "decoder": "utf-8-strict",
                "lossy_decoding_used": False,
                "raw_byte_count": len(raw_output),
                "raw_sha256": raw_sha256,
                "error": problem,
            },
            **log_evidence,
        }

    if decode_provenance["payload_sha256"] != raw_sha256:
        raise RuntimeError("subprocess raw-byte digest changed across strict decoding")
    print(f"===== {label} =====\n{output}", flush=True)
    terminal = parse_terminal_summary(output, expected_token=result_token)
    executed = terminal["tests_run"]
    output_signatures = classify(output)
    ok = (completed.returncode == 0 and executed is not None and executed >= minimum
          and terminal["summary_complete"] and terminal["status"] == "OK")
    return {
        "suite": label, "executed": executed, "minimum": minimum,
        "exit_code": completed.returncode, "status": "PASS" if ok else "FAIL",
        "terminal_unittest_summary": terminal,
        "symptom_counts": output_signatures,
        "captured_output_symptom_counts": output_signatures,
        "symptom_counts_scope": (
            "all decoded UTF-8 subprocess output, including nested unittest runs and "
            "intentional negative controls; use terminal_unittest_summary for "
            "the authoritative status/counts of this suite invocation"
        ),
        "subprocess_output_decoding": {
            "status": "ACCEPTED",
            **decode_provenance,
        },
        **log_evidence,
    }


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
        # Synthetic regression checkouts may omit scripts/; stage the tracked helper.
        helper_source = Path(__file__).resolve().with_name("unittest_discover_with_result.py")
        if not helper_source.is_file():
            raise FileNotFoundError("Tracked unittest discovery helper is missing: " + str(helper_source))
        helper_target = checkout / "scripts" / helper_source.name
        helper_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(helper_source, helper_target)
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
        stage_workflow_fixtures(checkout / ".github", tests / ".github")
        stage_historical_upgrade_workflow(sources, tests)
        version = checkout / "07-Manifestes" / "VERSION"
        if version.is_file():
            dest = tests / "VERSION"
            if dest.exists() and dest.read_bytes() != version.read_bytes():
                raise RuntimeError("VERSION collision")
            if not dest.exists():
                shutil.copy2(version, dest)
        env = os.environ.copy()
        # Windows default text encoding can be cp1252; historical sources are UTF-8.
        # Enforce UTF-8 for Path.read_text/open as well as stdout/stderr.
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONPATH"] = os.pathsep.join(filter(None, [
            str(tests), str(sources), str(checkout), env.get("PYTHONPATH")]))
        evidence_dir = report.parent if report else None
        rows = [run_suite(tests, "test_*.py", checkout, env, minimum_tests,
                          "historical", evidence_dir)]
        for nested in nested_files:
            rows.append(run_suite(nested.parent, nested.name, checkout, env, 1,
                                  nested.relative_to(tests).as_posix(), evidence_dir))
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
    # Windows console may still use cp1252 even when child tests use UTF-8.
    # Escape unrepresentable console glyphs without altering captured evidence.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
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
