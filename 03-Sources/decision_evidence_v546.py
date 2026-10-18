"""Conservative evidence completeness triage, never a proof of validity. Author: Abdelhalim Talbi."""
from collections import Counter


def assess_evidence(sheet):
    if not isinstance(sheet, dict) or not isinstance(sheet.get('id'), str) or not sheet['id'].strip():
        raise ValueError('invalid decision sheet')
    reference = sheet.get('evidence_reference', '')
    links = sheet.get('links', [])
    if not isinstance(reference, str) or not isinstance(links, list):
        raise ValueError('invalid evidence fields')
    if not all(isinstance(link, dict) for link in links):
        raise ValueError('invalid evidence link')
    problems = []
    if not reference.strip(): problems.append('reference_missing')
    if not links: problems.append('linked_alert_missing')
    for link in links:
        if not link.get('evidence_id'): problems.append('link_evidence_id_missing')
        if not link.get('earlier_sha256') or not link.get('later_sha256'):
            problems.append('link_hash_missing')
    flags = list(dict.fromkeys(problems))
    return {'decision_id': sheet['id'], 'state': 'incomplete' if flags else 'unqualified',
            'completeness_flags': flags, 'linked_alerts': len(links),
            'reference_present': bool(reference.strip()), 'evidence_sufficiency_verified': False,
            'requires_human_validation': True, 'production_activation': False}


def evidence_overview(sheets):
    if not isinstance(sheets, list): raise ValueError('invalid decision list')
    ids = [s.get('id') if isinstance(s, dict) else None for s in sheets]
    if any(not isinstance(i, str) or not i.strip() for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('invalid or duplicate decision id')
    assessments = [assess_evidence(s) for s in sheets]
    counts = Counter(a['state'] for a in assessments)
    return {'total': len(assessments), 'incomplete': counts['incomplete'],
            'unqualified': counts['unqualified'], 'qualified': 0,
            'evidence_sufficiency_verified': False, 'production_activation': False}
