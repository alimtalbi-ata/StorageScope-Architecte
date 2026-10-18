"""Read-only decision dossiers and evidence-gap triage. Author: Abdelhalim Talbi."""
from collections import defaultdict
import json
from decision_committee_v538 import committee_dashboard
from campaign_report_v530 import _atomic_write


def review_dossier(store, *, today=None, owner=None, status='all', deadline='all'):
    dashboard = committee_dashboard(store, today=today, owner=owner, status=status, deadline=deadline)
    verified = store.governance_report(today=today)
    by_id = {d['id']: d for d in verified['decisions']}
    links = defaultdict(list)
    for link in verified['links']:
        links[link['decision_id']].append(link)
    followups = defaultdict(list)
    for followup in verified['followups']:
        followups[followup['decision_id']].append(followup)
    sheets = []
    for entry in dashboard['agenda']:
        original = by_id[entry['id']]
        reasons = list(entry['reasons'])
        if not original['evidence'].strip():
            reasons.append('Référence de preuve absente')
        if not links[entry['id']]:
            reasons.append('Aucun événement vérifié associé')
        if original['status'] == 'IN_REVIEW' and not original['approval']:
            reasons.append('Décision en attente de validation')
        # A link alone is not a verification of evidence sufficiency.
        evidence_assessment = 'non_qualifiee' if links[entry['id']] else 'liens_absents'
        sheets.append({**entry, 'evidence_reference': original['evidence'],
                       'rationale': original['rationale'], 'approval': original['approval'],
                       'links': links[entry['id']], 'followups': followups[entry['id']],
                       'evidence_assessment': evidence_assessment,
                       'review_reasons': list(dict.fromkeys(reasons)),
                       'requires_human_review': bool(reasons) or original['status'] in ('OPEN','IN_REVIEW')})
    owners = defaultdict(lambda: {'count': 0, 'p1': 0, 'needs_review': 0})
    for sheet in sheets:
        bucket = owners[sheet['owner']]
        bucket['count'] += 1
        bucket['p1'] += sheet['priority'] == 'P1'
        bucket['needs_review'] += sheet['requires_human_review']
    return {'schema': 'storagescope.decision-review.v5.39', 'as_of': dashboard['as_of'],
            'filters': dashboard['filters'], 'global_kpis': dashboard['global_kpis'],
            'owner_summary': dict(sorted(owners.items())), 'decision_sheets': sheets,
            'audit_head': dashboard['audit_head'], 'audit_verified': True,
            'evidence_sufficiency_verified': False, 'recommendation_only': True,
            'production_activation': False, 'author': 'Abdelhalim Talbi'}


def export_review(store, destination, *, format='md', **filters):
    if format not in ('md', 'json'):
        raise ValueError('unsupported review format')
    data = review_dossier(store, **filters)
    if format == 'json':
        content = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    else:
        content = '# Dossier de revue des décisions — StorageScope v5.39\n\n'
        content += f"Date : {data['as_of']} | Audit : `{data['audit_head']}`\n\n"
        content += '## Répartition par responsable\n\n'
        for owner, counts in data['owner_summary'].items():
            content += f"- {owner.replace(chr(10),' ')} : {counts['count']} décisions, {counts['p1']} P1, {counts['needs_review']} à examiner\n"
        for sheet in data['decision_sheets']:
            clean = lambda x: str(x).replace('\n', ' ').replace('\r', ' ')
            content += f"\n## {clean(sheet['id'])} — {clean(sheet['subject'])}\n\n"
            content += f"Responsable : {clean(sheet['owner'])} | Statut : {clean(sheet['status'])} | Échéance : {sheet['due_date']} | Priorité : {sheet['priority']}\n\n"
            content += f"Référence : {clean(sheet['evidence_reference'])} | Qualification : {sheet['evidence_assessment']}\n\n"
            for reason in sheet['review_reasons']:
                content += f"- {clean(reason)}\n"
        content += '\n*Revue humaine requise ; aucune activation en production. La suffisance des preuves n’est pas certifiée.*\n'
    _atomic_write(destination, content)
    return data
