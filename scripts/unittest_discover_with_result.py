#!/usr/bin/env python3
"""Run unittest discovery and emit one authoritative, machine-readable result.

The JSON marker is written only after test output streams are flushed. This is
important when tests spawn subprocesses that intentionally fail: merging the
parent's stderr and stdout can otherwise reorder nested summaries on Windows.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import unittest
from pathlib import Path

MARKER = "STORAGESCOPE_UNITTEST_RESULT: "


def emit_result(payload: dict) -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except (AttributeError, OSError):
            pass
    sys.stderr.write(MARKER + json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    sys.stderr.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, type=Path)
    parser.add_argument("--pattern", required=True)
    args = parser.parse_args()

    start = args.start.resolve()
    if not start.is_dir():
        emit_result({"status": "FAILED", "tests_run": 0, "failures": 0,
                     "errors": 1, "skipped": 0, "expected_failures": 0,
                     "unexpected_successes": 0, "error": "discovery start is not a directory"})
        return 2

    started = time.monotonic()
    try:
        suite = unittest.defaultTestLoader.discover(str(start), pattern=args.pattern)
        result = unittest.TextTestRunner(stream=sys.stderr, verbosity=0).run(suite)
        payload = {
            "status": "OK" if result.wasSuccessful() else "FAILED",
            "tests_run": result.testsRun,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
            "expected_failures": len(result.expectedFailures),
            "unexpected_successes": len(result.unexpectedSuccesses),
            "duration_seconds": round(time.monotonic() - started, 6),
        }
        emit_result(payload)
        return 0 if result.wasSuccessful() else 1
    except Exception as exc:
        payload = {
            "status": "FAILED", "tests_run": 0, "failures": 0,
            "errors": 1, "skipped": 0, "expected_failures": 0,
            "unexpected_successes": 0,
            "error_type": type(exc).__name__, "error": str(exc),
            "duration_seconds": round(time.monotonic() - started, 6),
        }
        emit_result(payload)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
