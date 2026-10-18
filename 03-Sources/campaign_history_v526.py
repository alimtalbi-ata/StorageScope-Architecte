"""Transactional SQLite benchmark history, read-only recommendations. Author: Abdelhalim Talbi."""
import hashlib
import os
import tempfile
import json
import sqlite3
from pathlib import Path
from architecture_decisions_v536 import ClosingConnection
from benchmark_stability_v525 import audit_campaigns

SCHEMA = '''CREATE TABLE IF NOT EXISTS campaigns (id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), digest TEXT NOT NULL, payload TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_campaign_time ON campaigns(recorded_at, id);'''

def _canonical(campaign):
    if not isinstance(campaign, dict) or not isinstance(campaign.get('id'), str) or not campaign['id'].strip():
        raise ValueError('invalid campaign id')
    # Audit validation before persistence; no NaN, no malformed pair.
    audit_campaigns([campaign])
    raw = json.dumps(campaign, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return raw, hashlib.sha256(raw.encode()).hexdigest()

class CampaignHistory:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(SCHEMA)
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10, factory=ClosingConnection)
        try:
            db.execute('PRAGMA busy_timeout=10000')
            return db
        except BaseException:
            db.close()
            raise
    def add(self, campaign):
        raw, digest = _canonical(campaign)
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT digest FROM campaigns WHERE id=?', (campaign['id'],)).fetchone()
            if row:
                if row[0] != digest: raise ValueError('campaign id conflict: immutable history')
                return False
            db.execute('INSERT INTO campaigns(id,digest,payload) VALUES (?,?,?)', (campaign['id'],digest,raw))
        return True
    def list(self, limit=100):
        if type(limit) is not int or not 1 <= limit <= 10000: raise ValueError('invalid limit')
        with self._connect() as db:
            rows = db.execute('SELECT id,recorded_at,digest,payload FROM campaigns ORDER BY recorded_at,id LIMIT ?', (limit,)).fetchall()
        result=[]
        for ident, timestamp, digest, raw in rows:
            if hashlib.sha256(raw.encode()).hexdigest()!=digest: raise ValueError('campaign integrity failure: '+ident)
            result.append({'id':ident,'recorded_at':timestamp,'sha256':digest,'campaign':json.loads(raw)})
        return result
    def report(self, limit=100):
        records=self.list(limit)
        if not records: return {'selected_policy':'default','reason':'no_campaigns','recommendation_only':True,'production_activation':False,'campaign_count':0,'timeline':[],'alerts':[]}
        audit=audit_campaigns([r['campaign'] for r in records])
        audit['timeline']=[{'id':r['id'],'recorded_at':r['recorded_at'],'sha256':r['sha256']} for r in records]
        audit['alerts']=[] if audit['reason']=='candidate_stable_across_campaigns' else [{'severity':'warning','code':audit['reason'],'message':'Default policy retained; inspect campaign stability'}]
        return audit
    def export_json(self, path, limit=100):
        report=self.report(limit)
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Write the complete report before replacing the destination. A failed
        # serialization or disk write must never truncate an existing export.
        payload = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=destination.parent,
                                             prefix='.' + destination.name + '.', suffix='.tmp',
                                             delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return report
