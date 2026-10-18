"""StorageScope transactional store v6.25. Non-destructive governance snapshots."""
import sqlite3, json, hashlib, datetime
from pathlib import Path
SCHEMA_VERSION = 1

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

def connect(path):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(str(p), timeout=15, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=15000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    return conn

def migrate(conn):
    conn.execute("BEGIN IMMEDIATE")
    try:
        version=conn.execute("PRAGMA user_version").fetchone()[0]
        if version>SCHEMA_VERSION: raise ValueError("Database schema newer than application")
        if version<1:
            conn.execute("CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS snapshot_items (snapshot_id TEXT NOT NULL REFERENCES snapshots(id) ON DELETE RESTRICT, asset_id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(snapshot_id,asset_id))")
            conn.execute("PRAGMA user_version=1")
        conn.commit()
    except Exception:
        conn.rollback(); raise

def save_snapshot(path, assets):
    if not isinstance(assets,list): raise ValueError("Expected asset list")
    ids=[]
    for asset in assets:
        if not isinstance(asset,dict) or not isinstance(asset.get("id"),str) or not asset["id"].strip(): raise ValueError("Each asset needs a stable id")
        ids.append(asset["id"].strip())
    if len(set(ids))!=len(ids): raise ValueError("Duplicate asset ids")
    ordered=sorted(assets,key=lambda a:a["id"])
    payload=canonical(ordered); key=hashlib.sha256(payload.encode()).hexdigest()
    with connect(path) as conn:
        migrate(conn)
        conn.execute("BEGIN IMMEDIATE")
        try:
            now=datetime.datetime.now(datetime.timezone.utc).isoformat()
            conn.execute("INSERT OR IGNORE INTO snapshots VALUES (?,?,?)",(key,payload,now))
            for asset in ordered:
                conn.execute("INSERT OR IGNORE INTO snapshot_items VALUES (?,?,?)",(key,asset["id"],canonical(asset)))
            conn.commit()
        except Exception:
            conn.rollback(); raise
    return key

def load_snapshot(path,key):
    with connect(path) as conn:
        migrate(conn)
        row=conn.execute("SELECT payload FROM snapshots WHERE id=?",(key,)).fetchone()
        if row is None: raise KeyError(key)
        payload=row[0]
        if hashlib.sha256(payload.encode()).hexdigest()!=key: raise ValueError("Snapshot hash mismatch")
        assets=json.loads(payload)
        items=conn.execute("SELECT asset_id,payload FROM snapshot_items WHERE snapshot_id=?",(key,)).fetchall()
        if len(items)!=len(assets) or {i[0]:json.loads(i[1]) for i in items}!={a['id']:a for a in assets}: raise ValueError("Snapshot item mismatch")
        return assets
