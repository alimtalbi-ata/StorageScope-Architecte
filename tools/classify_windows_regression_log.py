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

DESCRIPTIONS = {
    "IMPORT_ROOT_OR_SOURCE_PATH": "Source imports fail because the test process cannot resolve modules or its import root.",
    "TEST_ARBORESCENCE_OR_CWD": "A test looks for a source/build file relative to the wrong directory or test tree.",
    "SQLITE_HANDLE_LIFECYCLE": "An open SQLite/file handle prevents Windows cleanup or a database lifecycle check fails.",
    "STALE_VERSION_EXPECTATION": "A historical assertion hard-codes a version inconsistent with canonical release metadata.",
    "STALE_SOURCE_CONTRACT": "A static source-fragment assertion no longer matches the implementation.",
    "WINDOWS_FIXTURE_OR_EXECUTABLE_STRUCTURE": "A synthetic PE/portable fixture is structurally invalid.",
    "RELEASE_BUILD_OR_SOURCE_CONTRACT": "A packaging/build/qualification contract fails and needs test-by-test review.",
    "ENCODING": "A Unicode codec exception is explicit in the log.",
    "MISSING_PATH_OR_FIXTURE": "A file/fixture is missing without a narrower root-cause signature.",
    "OTHER_NEEDS_MANUAL_TRIAGE": "No safe signature matched; do not guess the cause.",
}


def clean(line: str) -> str:
    return TIMESTAMP.sub("", ANSI.sub("", line.rstrip("\r\n"))).strip()


def classify_failure(detail: str) -> tuple[str, str, str]:
    d = detail.replace("\\", "/")
    checks = [
        (r"Unicode(?:Decode|Encode)Error|codec can't (?:decode|encode)", "ENCODING", "explicit Unicode codec exception", "high"),
        (r"WinError\s*32|unclosed database|database is locked|(?=.*PermissionError)(?=.*(?:sqlite|\.db|database))", "SQLITE_HANDLE_LIFECYCLE", "Windows file-lock/database-lifecycle signature", "high"),
        (r"FileNotFoundError|can't open file|No such file or directory", "TEST_ARBORESCENCE_OR_CWD", "missing path in qualification tree", "high"),
        (r"AssertionError:.*(?:6\.108.*6\.\d+|6\.\d+.*6\.108|AppVersion|release version|VERSION)", "STALE_VERSION_EXPECTATION", "hard-coded/drifted release-version contract", "high"),
        (r"ValueError: substring not found|AssertionError:.*(?:not found in|substring not found)", "STALE_SOURCE_CONTRACT", "static source-fragment contract no longer matches", "high"),
        (r"Invalid PE section count|Entry module absent", "WINDOWS_FIXTURE_OR_EXECUTABLE_STRUCTURE", "synthetic executable/portable fixture rejected", "high"),
        (r"ModuleNotFoundError: No module named|ImportError: Failed to import test module", "IMPORT_ROOT_OR_SOURCE_PATH", "test import chain failed", "medium"),
        (r"FileNotFoundError|can't open file|No such file or directory", "MISSING_PATH_OR_FIXTURE", "missing path/fixture", "medium"),
        (r"AssertionError|ValueError|TypeError|AttributeError|KeyError|OSError|ImportError", "RELEASE_BUILD_OR_SOURCE_CONTRACT", "build/source assertion or exception", "low"),
    ]
    for pattern, category, signature, confidence in checks:
        if re.search(pattern, d, re.I | re.M):
            if category == "TEST_ARBORESCENCE_OR_CWD" and "04-Tests-et-Qualification" not in d:
                continue
            return category, signature, confidence
    return "OTHER_NEEDS_MANUAL_TRIAGE", "no known signature matched", "low"


def parse_unittest_log(text: str):
    entries, summary, current = [], {}, None

    def flush():
        nonlocal current
        if current is None:
            return
        detail = "\n".join(current.pop("_detail", []))
        category, signature, confidence = classify_failure(detail)
        current.update(detail=detail, category=category, signature=signature, confidence=confidence)
        entries.append(current)
        current = None

    for raw in text.splitlines():
        line = clean(raw)
        match = RECORD.match(line)
        if match:
            flush()
            current = {"kind": match.group(1), "test": match.group(2), "_detail": []}
            continue
        if SUMMARY.match(line):
            flush()
            ran = re.match(r"Ran\s+(\d+)\s+tests?\s+in\s+([0-9.]+)s", line)
            failed = re.match(r"FAILED\s*\(\s*failures=(\d+)\s*,\s*errors=(\d+)\s*\)", line)
            if ran:
                summary.update(tests_run=int(ran.group(1)), duration_seconds=float(ran.group(2)))
            if failed:
                summary.update(failures=int(failed.group(1)), errors=int(failed.group(2)))
            continue
        if current is not None:
            current["_detail"].append(line)
    flush()
    summary.update(
        observed_records=len(entries),
        observed_failures=sum(e["kind"] == "FAIL" for e in entries),
        observed_errors=sum(e["kind"] == "ERROR" for e in entries),
    )
    summary["counts_match_summary"] = (
        summary.get("failures", summary["observed_failures"]) == summary["observed_failures"]
        and summary.get("errors", summary["observed_errors"]) == summary["observed_errors"]
    )
    return entries, summary


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
        ],
    }


def render_markdown(report):
    s = report["summary"]
    lines = ["# StorageScope - classification des echecs Windows historiques", "",
             "**Auteur :** " + report["author"],
             "**Run :** " + str(report.get("run_id") or "non precise"),
             "**Log :** " + str(report["source_log"]),
             "**Genere UTC :** " + report["generated_at_utc"], "",
             "## Synthese", "",
             "- Tests declares : " + str(s.get("tests_run", "non trouve")),
             "- Echecs : " + str(s["observed_failures"]) + " (resume " + str(s.get("failures", "absent")) + ")",
             "- Erreurs : " + str(s["observed_errors"]) + " (resume " + str(s.get("errors", "absent")) + ")",
             "- Enregistrements : " + str(s["observed_records"]),
             "- Comptes coherents : " + str(s["counts_match_summary"]),
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
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args(argv)
    try:
        raw = args.log.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        parser.error("cannot read UTF-8 log: " + str(exc))
    entries, summary = parse_unittest_log(raw)
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
        print("WARNING: extracted counts disagree with unittest summary; manual review required.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
