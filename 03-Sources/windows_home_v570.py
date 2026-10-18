"""Presentation model for StorageScope home dashboard. Author: Abdelhalim Talbi."""

# Prioritise everyday tasks; diagnostics and maintenance remain secondary.
CARDS = (
    ('Gouvernance', 'Suivre les décisions', 'Consulter les décisions, échéances et validations du comité.', 'Ouvrir les décisions', 'quotidien'),
    ('Campagnes', 'Analyser les campagnes', 'Comparer les campagnes et leurs indicateurs de validation.', 'Comparer les campagnes', 'quotidien'),
    ('Diagnostic', 'Vérifier la santé', 'Contrôler les bases locales et comprendre une anomalie.', 'Lancer le diagnostic', 'support'),
    ('Maintenance', 'Protéger les données', 'Créer une sauvegarde vérifiée des bases et vues.', 'Gérer les sauvegardes', 'support'),
)

def home_cards():
    return tuple({'page': page, 'title': title, 'description': description, 'action': action, 'group': group}
                 for page, title, description, action, group in CARDS)

def health_summary(states):
    """Never label missing or damaged databases healthy."""
    if not isinstance(states, dict) or any(key not in states for key in ('decisions', 'campaigns')):
        raise ValueError('missing health information')
    values = [str(states[key]) for key in ('decisions', 'campaigns')]
    if any(value.startswith('ERREUR') for value in values):
        return 'Anomalie détectée · ouvrir Diagnostic'
    if all(value == 'OK' for value in values):
        return '2 bases vérifiées'
    if all(value == 'ABSENTE' for value in values):
        return 'Nouvel espace · aucune base créée'
    if all(value in ('OK', 'ABSENTE') for value in values):
        return 'Espace partiellement initialisé'
    return 'État inconnu · ouvrir Diagnostic'
