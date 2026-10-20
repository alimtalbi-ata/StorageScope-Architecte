"""Read-only, privacy-conscious Windows support diagnostics.

No database creation, SQL data extraction, network requests or user paths in exports.
Author: Abdelhalim Talbi.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import platform
import sqlite3
from contextlib import closing

def _sqlite_state(path):
    path = Path(path)
    if path.is_symlink():
        return {"status": "ERROR", "reason": "symbolic link"}
    if not path.exists():
        return {"status": "MISSING"}
    if not path.is_file():
        return {"status": "ERROR", "reason": "not a regular file"}
    try:
        uri = path.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True, timeout=2)) as db:
            result = db.execute("PRAGMA quick_check").fetchone()
        if result and result[0] == "ok":
            return {"status": "OK", "size_bytes": path.stat().st_size}
        return {"status": "ERROR", "reason": "SQLite integrity check failed"}
    except (OSError, sqlite3.Error, ValueError):
        return {"status": "ERROR", "reason": "SQLite unavailable or unreadable"}

def classify_check(result):
    """Severity and actionable guidance without altering stored data."""
    status = result["status"]
    reason = result.get("reason", "")
    if status == "OK":
        return {"severity": "INFO", "recommendation": "Aucune action nécessaire."}
    if status == "MISSING":
        return {"severity": "NOTICE", "recommendation": "Vérifier si cet espace a été initialisé ; sinon aucune action requise."}
    if reason == "symbolic link":
        advice = "Utiliser un fichier local régulier ; vérifier le chemin configuré."
    elif reason == "not a regular file":
        advice = "Vérifier le type de fichier et ses droits d'accès."
    elif "integrity" in reason.lower():
        advice = "Conserver une copie, puis envisager une restauration depuis une sauvegarde vérifiée."
    else:
        advice = "Vérifier les droits et l'espace disque avant toute intervention."
    return {"severity": "ERROR", "recommendation": advice}

def filter_checks(report, severity="ALL"):
    if severity not in ("ALL", "ERROR", "NOTICE", "INFO"):
        raise ValueError("Unsupported diagnostic severity")
    return {name: value for name, value in report["checks"].items()
            if severity == "ALL" or value["severity"] == severity}

def collect(paths, version):
    """Return a structured report without exposing database records or absolute paths."""
    checks = {name: _sqlite_state(paths[name]) for name in ("decisions", "campaigns")}
    preferences = Path(paths["preferences"])
    checks["preferences"] = (
        {"status": "ERROR", "reason": "symbolic link"} if preferences.is_symlink()
        else {"status": "OK"} if preferences.is_file()
        else {"status": "MISSING"} if not preferences.exists()
        else {"status": "ERROR", "reason": "not a regular file"}
    )
    checks = {name: {**value, **classify_check(value)} for name, value in checks.items()}
    counts = {state: sum(1 for value in checks.values() if value["status"] == state)
              for state in ("OK", "MISSING", "ERROR")}
    return {
        "schema": "storagescope-support-diagnostic-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "application": {"name": "StorageScope", "version": str(version)},
        "runtime": {"python": platform.python_version(), "system": platform.system(),
                    "release": platform.release()},
        "checks": checks,
        "summary": counts,
        "privacy": "No user paths, database records, usernames or environment variables collected.",
    }

def render(report, severity="ALL"):
    lines = [
        f"StorageScope {report['application']['version']} — Diagnostic support",
        f"Date UTC : {report['created_utc']}",
        f"Système : {report['runtime']['system']} {report['runtime']['release']}",
        f"Python : {report['runtime']['python']}",
        "",
    ]
    for name, result in filter_checks(report, severity).items():
        suffix = f" ({result['reason']})" if "reason" in result else ""
        lines.append(f"[{result['severity']}] {name} : {result['status']}{suffix}")
        if result["status"] != "OK":
            lines.append("  Conseil : " + result["recommendation"])
    summary = report["summary"]
    lines.extend(["", f"Contrôles : {summary['OK']} OK · {summary['MISSING']} absents · {summary['ERROR']} erreurs",
                  "Rapport local en lecture seule, sans données métier ni chemins personnels."])
    return "\n".join(lines)

def export_json(report, destination):
    """Create exclusively; refuse existing files and symbolic links."""
    destination = Path(destination)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    with destination.open("x", encoding="utf-8") as stream:
        stream.write(payload)
    return destination
