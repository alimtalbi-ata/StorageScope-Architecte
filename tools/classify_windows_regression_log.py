#!/usr/bin/env python3
"""Rule-based triage of unittest FAIL/ERROR records from Windows build logs.

A triage aid only: it keeps ambiguous rows visible and never claims a source bug
has been fixed. Author: Abdelhalim Talbi.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\S+Z\s?")
RECORD = re.compile(r"^(FAIL|ERROR):\s+(.+)$")
SUMMARY = re.compile(r"^(?:Ran\s+\d+\s+tests?\b|FAILED\s*\(|OK(?:\s*\(.*\))?\s*$)")
RUN_SUMMARY_LINE = re.compile(r"Ran\s+(?P<count>\d+)\s+tests?\s+in\s+(?P<seconds>[0-9]+(?:\.[0-9]+)?)s")
FAILED_SUMMARY_LINE = re.compile(r"FAILED\s*\((.*)\)")
# Standard unittest success details may report skipped tests and expected failures.
# Unknown payloads are not evidence of a successful test run.
OK_SUMMARY_LINE = re.compile(
    r"OK(?:\s*\((?:skipped=\d+(?:,\s*expected failures=\d+)?|"
    r"expected failures=\d+(?:,\s*skipped=\d+)?)\))?"
)

DESCRIPTIONS = {
    "IMPORT_ROOT_OR_SOURCE_PATH": "Source imports fail because the test process cannot resolve modules or its import root.",
    "TEST_ARBORESCENCE_OR_CWD": "A test looks for a source/build file relative to the wrong directory or test tree.",
    "SQLITE_HANDLE_LIFECYCLE": "An open SQLite/file handle prevents Windows cleanup or a database lifecycle check fails.",
    "STALE_VERSION_EXPECTATION": "A historical assertion hard-codes a version inconsistent with canonical release metadata.",
    "STALE_SOURCE_CONTRACT": "A static source-fragment assertion no longer matches the implementation.",
    "WINDOWS_FIXTURE_OR_EXECUTABLE_STRUCTURE": "A synthetic PE/portable fixture is structurally invalid.",
    "RELEASE_BUILD_OR_SOURCE_CONTRACT": "A packaging/build/qualification contract fails and needs test-by-test review.",
    "ENCODING": "A Unicode codec exception is explicit in the log.",
    "MISSING_TEST_DEPENDENCY": "A test explicitly requires an optional library that is absent from the test environment.",
    "MISSING_PATH_OR_FIXTURE": "A file/fixture is missing without a narrower root-cause signature.",
    "OTHER_NEEDS_MANUAL_TRIAGE": "No safe signature matched; do not guess the cause.",
}


def clean(line: str) -> str:
    return TIMESTAMP.sub("", ANSI.sub("", line.rstrip("\r\n"))).strip()


def classify_failure(detail: str, test_name: str = "") -> tuple[str, str, str]:
    """Classify from the terminal exception and test name, not arbitrary source excerpts.

    Tracebacks can embed source lines containing words such as VERSION or "not found in".
    Those excerpts must not override the exception that actually caused the test failure.
    """
    lines = [line.strip() for line in detail.splitlines() if line.strip()]
    exception_re = re.compile(r"(?:[A-Za-z_]\w*(?:Error|Exception)|AssertionError):\s*.*")
    exception_lines = [line for line in lines if exception_re.search(line)]
    signature_text = exception_lines[-1] if exception_lines else (lines[-1] if lines else detail)
    signature = signature_text.replace("\\", "/")
    context = detail.replace("\\", "/")
    name = test_name.lower()
    assertion_claim = signature.split(" not found in ", 1)[0]

    checks = [
        (r"Unicode(?:Decode|Encode)Error|codec can't (?:decode|encode)", "ENCODING", "explicit Unicode codec exception", "high"),
        (r"WinError\s*32|unclosed database|database is locked|(?:PermissionError.*(?:sqlite|\.db|database))", "SQLITE_HANDLE_LIFECYCLE", "Windows file-lock/database-lifecycle signature", "high"),
        (r"FileNotFoundError|can't open file|No such file or directory", "TEST_ARBORESCENCE_OR_CWD", "missing path under the repository test/qualification tree", "high"),
        (r"PNG export requires Pillow|No module named ['\"]?PIL|No module named ['\"]?Pillow", "MISSING_TEST_DEPENDENCY", "test environment lacks the Pillow imaging dependency", "high"),
    ]
    for pattern, category, message, confidence in checks:
        if re.search(pattern, signature, re.I | re.M):
            if category == "TEST_ARBORESCENCE_OR_CWD" and "04-Tests-et-Qualification" not in context:
                continue
            if category == "SQLITE_HANDLE_LIFECYCLE" and not re.search(
                r"WinError\s*32|unclosed database|database is locked|(?:PermissionError.*(?:sqlite|\.db|database))",
                signature, re.I
            ):
                continue
            return category, message, confidence

    # Release tests explicitly named "version"/"manifest" frequently assert against a
    # legacy version literal rather than a runtime defect. Use only the assertion claim
    # (the text before "not found in") and the test identity, never source excerpt text.
    version_test = re.search(r"test.*(?:version|versions|manifest)", name, re.I) is not None
    version_claim = re.search(
        r"\b\d+\.\d+\b|AppVersion|VERSION\s*=|expectedVersion|StorageScope-Setup-v\d+\.\d+",
        assertion_claim, re.I
    ) is not None
    direct_version_mismatch = re.search(
        r"AssertionError:.*(?:\b6\.108\b.*\b6\.\d+\b|\b6\.\d+\b.*\b6\.108\b)",
        signature, re.I
    ) is not None
    if "AssertionError" in signature and (direct_version_mismatch or (version_test and version_claim)):
        return "STALE_VERSION_EXPECTATION", "release-version assertion uses a legacy literal", "high"

    if re.search(r"ValueError: substring not found", signature, re.I) or (
        "AssertionError" in signature and "not found in" in signature
    ):
        return "STALE_SOURCE_CONTRACT", "static source-fragment assertion no longer matches the implementation", "high"

    if re.search(r"Invalid PE section count|Entry module absent", signature, re.I):
        return "WINDOWS_FIXTURE_OR_EXECUTABLE_STRUCTURE", "synthetic executable/portable fixture rejected", "high"

    if re.search(r"ModuleNotFoundError: No module named|ImportError: Failed to import test module", signature, re.I):
        return "IMPORT_ROOT_OR_SOURCE_PATH", "test import chain failed", "medium"

    if re.search(r"FileNotFoundError|can't open file|No such file or directory", signature, re.I):
        return "MISSING_PATH_OR_FIXTURE", "missing path/fixture outside the known test-tree signature", "medium"

    if re.search(r"AssertionError|ValueError|TypeError|AttributeError|KeyError|OSError|ImportError|NameError", signature, re.I):
        return "RELEASE_BUILD_OR_SOURCE_CONTRACT", "build/source assertion or exception requiring review", "low"

    return "OTHER_NEEDS_MANUAL_TRIAGE", "no known exception signature matched", "low"

def parse_unittest_log(text: str, expected_tests: int | None = None):
    """Parse one unittest invocation and fail closed on missing/ambiguous summaries.

    A partial log must never be considered internally consistent merely because a
    summary line was absent. Use --expected-tests when auditing a known historical
    suite whose declared test count is part of the evidence contract.
    """
    entries, summary, current = [], {
        "summary_present": False,
        "summary_complete": False,
        "run_summary_lines": 0,
        "result_summary_lines": 0,
        "trailing_output_lines": 0,
        "summary_problem": [],
        "failed_summary_fields_valid": True,
        "failed_summary_problem": [],
    }, None

    def flush():
        nonlocal current
        if current is None:
            return
        detail = "\n".join(current.pop("_detail", []))
        category, signature, confidence = classify_failure(detail, current["test"])
        current.update(detail=detail, category=category, signature=signature, confidence=confidence)
        entries.append(current)
        current = None

    for raw in text.splitlines():
        line = clean(raw)
        if not line:
            continue
        # The input contract is one isolated unittest invocation. Once its final
        # OK/FAILED line appears, non-summary output makes the evidence ambiguous.
        is_complete_summary = bool(
            RUN_SUMMARY_LINE.fullmatch(line)
            or FAILED_SUMMARY_LINE.fullmatch(line)
            or OK_SUMMARY_LINE.fullmatch(line)
        )
        if summary.get("result_summary_lines", 0) and not is_complete_summary:
            summary["trailing_output_lines"] += 1
        match = RECORD.match(line)
        if match:
            flush()
            current = {"kind": match.group(1), "test": match.group(2), "_detail": []}
            continue
        if SUMMARY.match(line):
            flush()
            ran = RUN_SUMMARY_LINE.fullmatch(line)
            if ran:
                summary["run_summary_lines"] += 1
                summary.update(
                    tests_run=int(ran.group("count")),
                    duration_seconds=float(ran.group("seconds")),
                )
                summary["summary_present"] = True
                continue

            failed = FAILED_SUMMARY_LINE.fullmatch(line)
            if failed:
                summary["result_summary_lines"] += 1
                summary["result_status"] = "FAILED"
                summary["summary_present"] = True
                count_pairs = re.findall(r"\b(failures|errors|skipped)=(\d+)\b", failed.group(1))
                declared = dict(count_pairs)
                residual = re.sub(r"\b(?:failures|errors|skipped)=\d+\b", "", failed.group(1))
                residual = residual.replace(",", "").strip()
                if len(count_pairs) != len(declared):
                    summary["failed_summary_fields_valid"] = False
                    summary["failed_summary_problem"].append("FAILED summary contains duplicate count fields")
                if residual:
                    summary["failed_summary_fields_valid"] = False
                    summary["failed_summary_problem"].append("FAILED summary contains unrecognized count fields")
                if ("failures" in declared or "errors" in declared) and summary["failed_summary_fields_valid"]:
                    # unittest omits zero-valued categories from FAILED summaries.
                    summary.update(
                        failures=int(declared.get("failures", 0)),
                        errors=int(declared.get("errors", 0)),
                    )
                    if summary["failures"] + summary["errors"] == 0:
                        summary["failed_summary_fields_valid"] = False
                        summary["failed_summary_problem"].append(
                            "FAILED summary declares zero failures and errors"
                        )
                else:
                    summary["failed_summary_fields_valid"] = False
                    if "failures" not in declared and "errors" not in declared:
                        summary["failed_summary_problem"].append("FAILED summary does not contain parseable failure/error totals")
                continue

            if OK_SUMMARY_LINE.fullmatch(line):
                summary["result_summary_lines"] += 1
                summary["result_status"] = "OK"
                summary.update(failures=0, errors=0)
                summary["summary_present"] = True
                continue
        if current is not None:
            current["_detail"].append(line)
    flush()

    summary.update(
        observed_records=len(entries),
        observed_failures=sum(e["kind"] == "FAIL" for e in entries),
        observed_errors=sum(e["kind"] == "ERROR" for e in entries),
    )
    problems = list(summary.get("failed_summary_problem", []))
    if summary["run_summary_lines"] == 0:
        problems.append("missing Ran <n> tests summary")
    elif summary["run_summary_lines"] != 1:
        problems.append("expected exactly one unittest run summary; found " + str(summary["run_summary_lines"]))
    if summary["result_summary_lines"] == 0:
        problems.append("missing final OK/FAILED summary")
    elif summary["result_summary_lines"] != 1:
        problems.append("expected exactly one unittest result summary; found " + str(summary["result_summary_lines"]))
    if summary.get("result_status") == "FAILED" and ("failures" not in summary or "errors" not in summary):
        problems.append("FAILED summary does not contain parseable failures and errors totals")
    if summary["trailing_output_lines"]:
        problems.append(
            "unexpected non-empty output after unittest result summary: "
            + str(summary["trailing_output_lines"]) + " line(s)"
        )

    summary["summary_complete"] = (
        summary["failed_summary_fields_valid"]
        and summary["trailing_output_lines"] == 0
        and summary["run_summary_lines"] == 1
        and summary["result_summary_lines"] == 1
        and "tests_run" in summary
        and summary.get("result_status") in ("FAILED", "OK")
        and "failures" in summary
        and "errors" in summary
    )
    counts_match = (
        summary["summary_complete"]
        and summary["failures"] == summary["observed_failures"]
        and summary["errors"] == summary["observed_errors"]
        and summary["tests_run"] >= summary["observed_records"]
        and (summary["result_status"] != "OK" or summary["observed_records"] == 0)
    )
    if summary["summary_complete"] and not counts_match:
        problems.append("declared summary totals do not match extracted FAIL/ERROR records or test count")
    if expected_tests is not None:
        summary["expected_tests"] = expected_tests
        summary["expected_tests_match"] = summary.get("tests_run") == expected_tests
        if not summary["expected_tests_match"]:
            problems.append("declared test count does not match expected count " + str(expected_tests))
            counts_match = False
    summary["summary_problem"] = problems
    summary["counts_match_summary"] = bool(counts_match)
    return entries, summary

def extract_failed_unittest_block_from_job_log(text: str) -> tuple[str, dict[str, object]]:
    """Bound one failed unittest invocation inside a complete GitHub Actions job log.

    The strict parser remains unchanged. This opt-in adapter accepts wrapper output
    only after the terminal summary, and only when the full job log contains exactly
    one unittest run summary and one FAILED summary. Multiple runs, post-summary
    FAIL/ERROR records, successful runs, or missing records are refused.
    """
    lines = text.splitlines()
    cleaned = [clean(line) for line in lines]
    run_indexes = [
        index for index, line in enumerate(cleaned)
        if RUN_SUMMARY_LINE.fullmatch(line)
    ]
    result_indexes = [
        index for index, line in enumerate(cleaned)
        if FAILED_SUMMARY_LINE.fullmatch(line) or OK_SUMMARY_LINE.fullmatch(line)
    ]
    if len(run_indexes) != 1:
        raise ValueError(
            "expected exactly one unittest run summary in full job log; found "
            + str(len(run_indexes))
        )
    if len(result_indexes) != 1:
        raise ValueError(
            "expected exactly one unittest result summary in full job log; found "
            + str(len(result_indexes))
        )

    run_index = run_indexes[0]
    result_index = result_indexes[0]
    if result_index <= run_index:
        raise ValueError("unittest result summary must follow the run summary")
    if not FAILED_SUMMARY_LINE.fullmatch(cleaned[result_index]):
        raise ValueError(
            "job-log extraction is reserved for failed unittest runs; "
            "parse an isolated successful unittest output directly"
        )

    record_indexes = [
        index for index, line in enumerate(cleaned) if RECORD.fullmatch(line)
    ]
    if not record_indexes:
        raise ValueError("no unittest FAIL/ERROR records found before failed summary")
    if any(index > result_index for index in record_indexes):
        raise ValueError("unittest FAIL/ERROR record found after terminal summary")
    if any(index >= run_index for index in record_indexes):
        raise ValueError("unittest FAIL/ERROR records must precede the run summary")

    start_index = record_indexes[0]
    bounded = "\n".join(lines[start_index:result_index + 1]) + "\n"
    bounds = {
        "mode": "explicit_failed_unittest_block",
        "source_line_start": start_index + 1,
        "source_line_end": result_index + 1,
        "run_summary_line": run_index + 1,
        "result_summary_line": result_index + 1,
        "test_records": len(record_indexes),
        "wrapper_lines_excluded_after_result": len(lines) - result_index - 1,
    }
    return bounded, bounds


def make_report(entries, summary, run_id, source):
    counts = {}
    for entry in entries:
        bucket = counts.setdefault(entry["category"], Counter())
        bucket[entry["kind"]] += 1
    return {
        "schema": "storagescope.windows-historical-failure-taxonomy.v1",
        "author": "Abdelhalim Talbi",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "source_log": source,
        "summary": summary,
        "classification_is_heuristic": True,
        "unclassified_count": counts.get("OTHER_NEEDS_MANUAL_TRIAGE", Counter()).total(),
        "categories": [
            {"category": name, "description": DESCRIPTIONS[name], "failures": bucket["FAIL"],
             "errors": bucket["ERROR"], "total": bucket["FAIL"] + bucket["ERROR"]}
            for name, bucket in sorted(counts.items())
        ],
        "items": [{k: v for k, v in entry.items() if k != "detail"} for entry in entries],
        "limitations": [
            "Classification is heuristic and does not prove a defect is fixed.",
            "Broad release/build-contract categories require full-traceback review.",
            "Zero codec-error matches only describes this log, not encoding correctness in general.",
            "A missing, duplicated, truncated, inconsistent, zero-count FAILED, or trailing-output unittest summary fails closed; use --expected-tests for a known historical suite.",
            "For complete workflow logs, --extract-failed-unittest-block is explicit and fail-closed: it requires one failed unittest invocation and rejects ambiguous summaries or post-summary test records.",
        ],
    }


def render_markdown(report):
    s = report["summary"]
    lines = ["# StorageScope - classification des echecs Windows historiques", "",
             "**Auteur :** " + report["author"],
             "**Run :** " + str(report.get("run_id") or "non precise"),
             "**Log :** " + str(report["source_log"]),
             "**Genere UTC :** " + report["generated_at_utc"],
             "**Portee entree :** " + str(s.get("input_scope", "isolated_unittest_output")),
             "**Bornes extraction :** " + (json.dumps(s["extraction"], ensure_ascii=False, sort_keys=True) if s.get("extraction") else "aucune"), "",
             "## Synthese", "",
             "- Tests declares : " + str(s.get("tests_run", "non trouve")),
             "- Echecs : " + str(s["observed_failures"]) + " (resume " + str(s.get("failures", "absent")) + ")",
             "- Erreurs : " + str(s["observed_errors"]) + " (resume " + str(s.get("errors", "absent")) + ")",
             "- Enregistrements : " + str(s["observed_records"]),
             "- Résumé présent/complet : " + str(s.get("summary_present")) + "/" + str(s.get("summary_complete")),
             "- Comptes cohérents : " + str(s["counts_match_summary"]),
             "- Problèmes de résumé : " + ("; ".join(s.get("summary_problem", [])) or "aucun"),
             "- Cas non classes automatiquement : " + str(report["unclassified_count"]), "",
             "## Causes racines probables", "",
             "| Categorie | Echecs | Erreurs | Total | Interpretation |",
             "|---|---:|---:|---:|---|"]
    for c in report["categories"]:
        lines.append("| " + c["category"] + " | " + str(c["failures"]) + " | " + str(c["errors"]) + " | " + str(c["total"]) + " | " + c["description"].replace("|", "\\|") + " |")
    lines += ["", "## Detail test par test", "", "| Type | Test | Categorie | Signature | Confiance |", "|---|---|---|---|---|"]
    for item in report["items"]:
        lines.append("| " + item["kind"] + " | " + item["test"].replace("|", "\\|") + " | " + item["category"] + " | " + item["signature"].replace("|", "\\|") + " | " + item["confidence"] + " |")
    lines += ["", "Ne desactiver aucun controle historique. Corriger les racines d'import/chemins, fermer les handles SQLite, puis rapprocher les contrats de version et packaging des sources canoniques.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="Raw UTF-8 GitHub Actions job log")
    parser.add_argument("--run-id")
    parser.add_argument("--expected-tests", type=int, help="Require the declared unittest test count to match this historical expectation")
    parser.add_argument("--extract-failed-unittest-block", action="store_true", help="Extract exactly one failed unittest block from a full GitHub Actions job log; ambiguity fails closed")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args(argv)
    if args.expected_tests is not None and args.expected_tests < 1:
        parser.error("--expected-tests must be a positive integer")
    try:
        raw = args.log.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        parser.error("cannot read UTF-8 log: " + str(exc))
    extraction = None
    if args.extract_failed_unittest_block:
        try:
            raw, extraction = extract_failed_unittest_block_from_job_log(raw)
        except ValueError as exc:
            print("ERROR: refusing to extract unittest output from job log: " + str(exc), file=sys.stderr)
            return 2
    entries, summary = parse_unittest_log(raw, expected_tests=args.expected_tests)
    summary["input_scope"] = "github_actions_job_log" if extraction else "isolated_unittest_output"
    if extraction is not None:
        summary["extraction"] = extraction
    if not entries:
        print("No unittest FAIL/ERROR records found; refusing empty classification.", file=sys.stderr)
        return 2
    report = make_report(entries, summary, args.run_id, str(args.log))
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(serialized, encoding="utf-8", newline="\n")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown(report), encoding="utf-8", newline="\n")
    if not args.json_output and not args.markdown_output:
        print(serialized, end="")
    if not summary["counts_match_summary"]:
        detail = "; ".join(summary.get("summary_problem", [])) or "summary counts are inconsistent"
        print("ERROR: refusing to qualify this log: " + detail, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
