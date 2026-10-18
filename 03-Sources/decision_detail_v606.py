"""Readable, read-only decision summary. Author: Abdelhalim Talbi."""

def decision_detail(sheet, evidence, quality, qualification):
    """Return a concise plain-text card without hiding missing evidence."""
    if not isinstance(sheet, dict) or not sheet.get('id'):
        raise ValueError('invalid decision')
    if not isinstance(evidence, dict) or not isinstance(quality, dict) or not isinstance(qualification, dict):
        raise ValueError('invalid detail sections')
    def field(key, default='Non renseigné'):
        value = sheet.get(key)
        return str(value).strip() if value is not None and str(value).strip() else default
    lines = [f"DÉCISION  {field('id')}", '─' * 48,
             f"Sujet : {field('subject')}", f"Statut : {field('status')}",
             f"Priorité : {field('priority')}", f"Responsable : {field('owner')}",
             f"Échéance : {field('due_date')}", f"Situation : {field('deadline_state')}",
             '', 'PREUVES ET VALIDATION',
             f"Référence : {field('evidence_reference')}",
             f"Revue humaine : {qualification.get('status') or 'Non revue'}",
             'Attention : une référence de preuve ne garantit pas sa suffisance.',
             '', 'ACTIONS DISPONIBLES',
             'Consulter la chronologie et les pièces justificatives via les commandes de gouvernance.',
             'Aucune modification de production depuis cette fiche.']
    if qualification.get('stale'):
        lines.insert(lines.index('ACTIONS DISPONIBLES'), 'Qualification à renouveler : oui')
    return '\n'.join(lines)
