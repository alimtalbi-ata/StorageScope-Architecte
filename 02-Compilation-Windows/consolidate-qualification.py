#!/usr/bin/env python3
"""Consolidate real Windows qualification evidence; never turn missing tests into PASS."""
import argparse, json, pathlib, sys, datetime
REQUIRED_NATIVE_CHECKS = ['release_version', 'build_launcher', 'release_manifest', 'compiled_executable', 'executable_version', 'executable_self_test', 'installer_present']
NAMES = {"native": "windows-qualification-report.json", "installer": "windows-installer-smoke-report.json", "portable": "windows-portable-smoke-report.json"}

def consolidate(root, min_timestamp=None):
    root = pathlib.Path(root)
    version = (root / "07-Manifestes/VERSION").read_text(encoding="utf-8").strip()
    base = root / "02-Compilation-Windows"
    reports = {}
    for name, filename in NAMES.items():
        path = base / filename
        if not path.is_file():
            reports[name] = {"status": "MISSING", "reason": filename}
            continue
        try:
            if min_timestamp is not None and path.stat().st_mtime < min_timestamp:
                reports[name] = {"status": "FAIL", "reason": "stale report"}
                continue
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            status = data.get("overall") if name == "native" else data.get("status")
            if not isinstance(data, dict) or status != "PASS" or data.get("version") != version:
                reports[name] = {"status": "FAIL", "reason": "status/version mismatch"}
            elif name == "native" and (not isinstance(data.get("checks"), list) or not data["checks"] or any(not isinstance(c, dict) or c.get("status") != "PASS" for c in data["checks"]) or len({c.get("name") for c in data["checks"] if isinstance(c, dict)}) != len(data["checks"]) or not set(REQUIRED_NATIVE_CHECKS).issubset({c.get("name") for c in data["checks"] if isinstance(c, dict)})):
                reports[name] = {"status": "FAIL", "reason": "incomplete native checks"}
            elif name == "installer" and not all(data.get(k) is True for k in ("installed", "version_checked", "uninstalled")):
                reports[name] = {"status": "FAIL", "reason": "incomplete installer evidence"}
            elif name == "portable" and not all(data.get(k) is True for k in ("archive_present", "extracted", "version_checked", "self_test", "cleanup")):
                reports[name] = {"status": "FAIL", "reason": "incomplete portable evidence"}
            else:
                reports[name] = {"status": "PASS"}
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            reports[name] = {"status": "FAIL", "reason": type(exc).__name__}
    return {"version": version, "status": "PASS" if all(r["status"] == "PASS" for r in reports.values()) else "FAIL", "qualification": reports}

def main():
    p=argparse.ArgumentParser();p.add_argument("--root",default=".");p.add_argument("--output",required=True);p.add_argument("--min-timestamp",type=float);a=p.parse_args()
    result=consolidate(a.root, a.min_timestamp)
    target=pathlib.Path(a.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return 0 if result["status"]=="PASS" else 1
if __name__=="__main__":sys.exit(main())
