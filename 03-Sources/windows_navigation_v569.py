"""Accent-insensitive, unambiguous module routing. Author: Abdelhalim Talbi."""
import unicodedata
ROUTES = {'Accueil': ('accueil','home'), 'Gouvernance': ('gouvernance','comite','decision','preuve','audit','architecture'), 'Campagnes': ('campagne','benchmark','performance','mesure'), 'Diagnostic': ('diagnostic','integrite','sqlite'), 'Maintenance': ('maintenance','sauvegarde','backup','donnees')}
def route(query):
    if not isinstance(query,str): raise TypeError('query must be text')
    value=''.join(c for c in unicodedata.normalize('NFKD',query.casefold()) if not unicodedata.combining(c)).strip()
    if not value: return None
    exact=[page for page,aliases in ROUTES.items() if value in aliases]
    if exact: return exact[0]
    candidates={page for page,aliases in ROUTES.items() if any(a.startswith(value) for a in aliases)}
    return next(iter(candidates)) if len(candidates)==1 else None
