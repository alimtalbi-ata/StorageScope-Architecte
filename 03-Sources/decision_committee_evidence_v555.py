"""Conservative committee evidence digest and verifiable export. Author: Abdelhalim Talbi."""
import json
from pathlib import Path
from decision_timeline_export_v554 import filtered_timeline
from campaign_report_v530 import _atomic_write


def committee_evidence_digest(store, ident):
    """Verify all events, retain the audit anchor, and never assert evidence sufficiency."""
    record = filtered_timeline(store, ident)
    events = record['events']
    reviews = [e for e in events if e['type'] == 'EVIDENCE_QUALIFIED']
    linked = [e for e in events if e['type'] == 'EVIDENCE_LINKED']
    references = [e['reference'] for e in events if e.get('reference')]
    evidence_ids = list(dict.fromkeys(e['evidence_id'] for e in linked if e.get('evidence_id')))
    latest = reviews[-1] if reviews else None
    return {'schema':'storagescope.committee-evidence.v5.55', 'decision_id':ident,
            'audit_head':record['audit_head'], 'event_count':len(events),
            'review_count':len(reviews), 'linked_evidence_count':len(linked),
            'evidence_references':references, 'linked_evidence_ids':evidence_ids,
            'current_state':record['current_state'],
            'latest_review':None if latest is None else {
                'audit_sequence':latest['sequence'], 'verdict':latest.get('qualification_verdict'),
                'stale':latest.get('qualification_stale')},
            'requires_human_review':record['current_state'] in ('STALE','UNREVIEWED'),
            'evidence_sufficiency_verified':False, 'production_activation':False,
            'author':'Abdelhalim Talbi'}


def export_committee_evidence(store, ident, destination, *, format='md'):
    if format not in ('md','json'):
        raise ValueError('unsupported format')
    digest=committee_evidence_digest(store, ident)
    if format=='json':
        content=json.dumps(digest,ensure_ascii=False,indent=2)+'\n'
    else:
        def safe(value):
            return str(value).replace('|','\\|').replace('\n',' ')
        latest=digest['latest_review']
        lines=['# Synthèse des preuves — comité d’architecture',
               '',f"Décision : {safe(ident)}",f"Tête d’audit SHA256 : `{digest['audit_head']}`",
               '',f"État de qualification : **{digest['current_state']}**",
               f"Événements : {digest['event_count']} · Revues : {digest['review_count']} · Preuves liées : {digest['linked_evidence_count']}",
               f"Dernière revue : {safe(latest['verdict']) if latest else 'Aucune'}",
               '', '## Références de preuves',
               *(f'- {safe(x)}' for x in digest['evidence_references']),
               *(f'- ID lié : {safe(x)}' for x in digest['linked_evidence_ids']),
               '', '**Validation humaine nécessaire :** '+('oui' if digest['requires_human_review'] else 'vérifier la suffisance'),
               '', 'Aucune suffisance des preuves certifiée. Aucune activation en production.',
               '', 'Auteur : Abdelhalim Talbi.']
        content='\n'.join(lines)+'\n'
    _atomic_write(Path(destination),content)
    return digest
