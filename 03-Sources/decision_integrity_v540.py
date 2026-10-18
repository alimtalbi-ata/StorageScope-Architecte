"""Fail-closed cross-table decision consistency and evidence navigation. Author: Abdelhalim Talbi."""
from collections import defaultdict
from decision_review_v539 import review_dossier
from architecture_decisions_v536 import TRANSITIONS


def consistency_report(store, *, today=None):
    data = store.governance_report(today=today)
    audit = data['audit']  # same transactional snapshot as decisions and links
    decisions = {d['id']: d for d in data['decisions']}
    issues = []
    def issue(code, ident, detail):
        issues.append({'code': code, 'decision_id': ident, 'detail': detail})
    created = defaultdict(list)
    transitions = defaultdict(list)
    linked = defaultdict(list)
    followed = defaultdict(list)
    event_stream = defaultdict(list)
    for entry in audit:
        event = entry['event']
        ident = entry['decision_id']
        event_stream[ident].append(event)
        if ident not in decisions or event.get('id') != ident:
            issue('orphan_audit', ident, 'Audit sans décision correspondante ou identifiant incohérent')
        if event.get('event') == 'CREATED': created[ident].append(event)
        if event.get('event') == 'TRANSITION': transitions[ident].append(event)
        if event.get('event') == 'EVIDENCE_LINKED': linked[ident].append(event)
        if event.get('event') == 'FOLLOWUP_RECORDED': followed[ident].append(event)
    for ident, d in decisions.items():
        if len(created[ident]) != 1:
            issue('creation_mismatch', ident, 'Événement de création absent ou dupliqué')
            continue
        events = event_stream[ident]
        if not events or events[0].get('event') != 'CREATED':
            issue('creation_order_mismatch', ident, 'La création doit être le premier événement')
        allowed = {'CREATED', 'TRANSITION', 'EVIDENCE_LINKED', 'FOLLOWUP_RECORDED', 'EVIDENCE_QUALIFIED', 'COMMITTEE_RESOLVED'}
        for event in events:
            if event.get('event') not in allowed:
                issue('unknown_audit_event', ident, str(event.get('event')))
        start = created[ident][0]
        for key in ('subject', 'owner', 'due_date', 'evidence'):
            if start.get(key) != d[key]: issue('immutable_field_mismatch', ident, key)
        state = 'OPEN'; rationale = ''; approval = ''
        for event in transitions[ident]:
            if event.get('to') not in TRANSITIONS.get(state, set()):
                issue('illegal_transition', ident, 'Transition non autorisée')
            if event.get('from') != state:
                issue('transition_chain_mismatch', ident, 'État précédent incohérent')
            state = event.get('to')
            rationale = event.get('rationale')
            approval = event.get('approval') or ''
        if (state, rationale, approval) != (d['status'], d['rationale'], d['approval']):
            issue('decision_state_mismatch', ident, 'État SQLite différent de l’historique')
        rows = [x for x in data['links'] if x['decision_id'] == ident]
        keys = ('earlier_id', 'later_id', 'alert_code', 'evidence_id', 'earlier_sha256', 'later_sha256')
        expected = {tuple(x.get(k) for k in keys) for x in linked[ident]}
        actual = {tuple(x.get(k) for k in keys) for x in rows}
        if len(expected) != len(linked[ident]) or len(actual) != len(rows): issue('duplicate_link', ident, 'Liens dupliqués')
        if actual != expected: issue('link_audit_mismatch', ident, 'Liens et événements d’audit différents')
        rows = [x for x in data['followups'] if x['decision_id'] == ident]
        expected = {(x.get('due_date'), x.get('actor'), x.get('note')) for x in followed[ident]}
        actual = {(x['due_date'], x['actor'], x['note']) for x in rows}
        if len(expected) != len(followed[ident]) or len(actual) != len(rows): issue('duplicate_followup', ident, 'Relances dupliquées')
        if actual != expected: issue('followup_audit_mismatch', ident, 'Relances et événements d’audit différents')
    for link in data['links']:
        if link['decision_id'] not in decisions:
            issue('orphan_link', link['decision_id'], 'Lien orphelin')
    for f in data['followups']:
        if f['decision_id'] not in decisions:
            issue('orphan_followup', f['decision_id'], 'Relance orpheline')
    return {'schema': 'storagescope.decision-consistency.v5.40', 'audit_head': data['audit_head'],
            'consistent': not issues, 'issues': issues, 'checked_decisions': len(decisions),
            'recommendation_only': True, 'production_activation': False, 'author': 'Abdelhalim Talbi'}


def verified_review(store, *, today=None, owner=None, status='all', deadline='all'):
    consistency = consistency_report(store, today=today)
    if not consistency['consistent']:
        raise ValueError('decision consistency failure: ' + ', '.join(sorted({x['code'] for x in consistency['issues']})))
    review = review_dossier(store, today=today, owner=owner, status=status, deadline=deadline)
    review['consistency'] = consistency
    return review


def decision_detail(store, ident, **filters):
    review = verified_review(store, **filters)
    matching = [x for x in review['decision_sheets'] if x['id'] == ident]
    if len(matching) != 1: raise KeyError(ident)
    return {'decision': matching[0], 'audit_head': review['audit_head'],
            'consistency_verified': True, 'recommendation_only': True, 'production_activation': False}
