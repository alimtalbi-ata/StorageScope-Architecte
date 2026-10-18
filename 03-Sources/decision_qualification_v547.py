"""Human evidence qualification ledger; never activates production. Author: Abdelhalim Talbi."""
import hashlib
import json
from architecture_decisions_v536 import _required, canonical
from decision_governance_v537 import GovernanceStore
from decision_integrity_v540 import consistency_report

CRITERIA = ('traceability', 'relevance', 'integrity', 'coverage')
VERDICTS = ('ACCEPT', 'REJECT', 'NEEDS_MORE_EVIDENCE')


def evidence_fingerprint(report, ident):
    decisions = [d for d in report['decisions'] if d['id'] == ident]
    if len(decisions) != 1: raise KeyError(ident)
    links = [l for l in report['links'] if l['decision_id'] == ident]
    return hashlib.sha256(canonical({'evidence': decisions[0]['evidence'], 'links': links}).encode()).hexdigest()


class QualificationStore(GovernanceStore):
    def __init__(self, path):
        super().__init__(path)
        with self._connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS evidence_qualifications (
              audit_seq INTEGER PRIMARY KEY, decision_id TEXT NOT NULL, actor TEXT NOT NULL,
              verdict TEXT NOT NULL, criteria TEXT NOT NULL, rationale TEXT NOT NULL,
              fingerprint TEXT NOT NULL)''')

    def qualify(self, ident, actor, verdict, criteria, rationale):
        ident = _required(ident, 'decision_id'); actor = _required(actor, 'actor')
        rationale = _required(rationale, 'rationale')
        if verdict not in VERDICTS: raise ValueError('invalid verdict')
        if not isinstance(criteria, dict) or set(criteria) != set(CRITERIA) or any(type(v) is not bool for v in criteria.values()):
            raise ValueError('all qualification criteria must be explicit booleans')
        if verdict == 'ACCEPT' and not all(criteria.values()):
            raise ValueError('cannot accept failed criteria')
        if not consistency_report(self)['consistent']:
            raise ValueError('decision registry inconsistent')
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            base = self._report_from_db(db)
            links = [dict(zip(('decision_id','earlier_id','later_id','alert_code','evidence_id','earlier_sha256','later_sha256'),r))
                     for r in db.execute('SELECT * FROM decision_links ORDER BY decision_id,earlier_id,later_id,alert_code,evidence_id')]
            fingerprint = evidence_fingerprint({'decisions':base['decisions'],'links':links}, ident)
            payload = {'event':'EVIDENCE_QUALIFIED','id':ident,'actor':actor,'verdict':verdict,
                       'criteria':criteria,'rationale':rationale,'fingerprint':fingerprint}
            self._append(db, ident, payload)
            seq = db.execute('SELECT last_insert_rowid()').fetchone()[0]
            db.execute('INSERT INTO evidence_qualifications VALUES (?,?,?,?,?,?,?)',
                       (seq,ident,actor,verdict,canonical(criteria),rationale,fingerprint))
        return {'decision_id':ident,'audit_seq':seq,'verdict':verdict,'fingerprint':fingerprint,
                'human_reviewed':True,'production_activation':False}

    def qualifications(self, ident=None):
        """Read audit, evidence links and qualifications in one SQLite snapshot.

        A mismatch is fatal even when the caller filters to one decision.
        """
        with self._connect() as db:
            db.execute('BEGIN')
            base = self._report_from_db(db)
            links = [dict(zip(('decision_id','earlier_id','later_id','alert_code','evidence_id','earlier_sha256','later_sha256'), r))
                     for r in db.execute('SELECT decision_id,earlier_id,later_id,alert_code,evidence_id,earlier_sha256,later_sha256 FROM decision_links ORDER BY decision_id,earlier_id,later_id,alert_code,evidence_id')]
            rows = db.execute('SELECT audit_seq,decision_id,actor,verdict,criteria,rationale,fingerprint FROM evidence_qualifications ORDER BY audit_seq').fetchall()
        audit = {x['seq']: x for x in base['audit']}
        report = {'decisions': base['decisions'], 'links': links}
        entries = []
        for seq, decision_id, actor, verdict, raw, rationale, fingerprint in rows:
            try:
                criteria = json.loads(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError('invalid qualification criteria') from exc
            if (verdict not in VERDICTS or not isinstance(criteria, dict) or
                set(criteria) != set(CRITERIA) or any(type(v) is not bool for v in criteria.values()) or
                (verdict == 'ACCEPT' and not all(criteria.values()))):
                raise ValueError('invalid qualification record')
            event = {'event': 'EVIDENCE_QUALIFIED', 'id': decision_id, 'actor': actor,
                     'verdict': verdict, 'criteria': criteria, 'rationale': rationale,
                     'fingerprint': fingerprint}
            if seq not in audit or audit[seq]['event'] != event or audit[seq]['decision_id'] != decision_id:
                raise ValueError('qualification audit mismatch')
            entries.append({'audit_seq': seq, 'decision_id': decision_id, 'actor': actor,
                            'verdict': verdict, 'criteria': criteria, 'rationale': rationale,
                            'fingerprint': fingerprint,
                            'stale': fingerprint != evidence_fingerprint(report, decision_id),
                            'production_activation': False})
        expected = {x['seq'] for x in base['audit'] if x['event'].get('event') == 'EVIDENCE_QUALIFIED'}
        if expected != {x['audit_seq'] for x in entries}:
            raise ValueError('missing qualification record')
        return [e for e in entries if ident is None or e['decision_id'] == ident]
