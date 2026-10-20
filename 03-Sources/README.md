# StorageScope — Sources Windows v6.108

Auteur : Abdelhalim Talbi.

## Application et objectifs

`storagescope_windows.py` est le point d'entrée Windows. Les parcours prioritaires sont : inventaire et réconciliation, gouvernance des décisions, campagnes, puis diagnostic et maintenance.

Le produit utilise actuellement Tkinter pour le shell et SQLite pour les données locales. La séparation progressive de la logique métier et de l'interface est préférable à un changement de framework non qualifié.

## Modules essentiels

- `governance_desktop.py` : revue des inventaires et réconciliation.
- `decision_workspace_ui_v543.py` et `decision_governance_v537.py` : décisions d'architecture.
- `campaign_dashboard_v527.py` et `campaign_history_v526.py` : campagnes et historique.
- `windows_support_diagnostic_v619.py` : rapport de diagnostic structuré, classifications, recommandations, filtre et export JSON.
- `storagescope_windows.py` : navigation, maintenance et shell Windows.

## Qualification

Le workflow `.github/workflows/diagnostic-regression.yml` doit exécuter `test_windows_support_diagnostic_v619.py`. Les workflows Windows vérifient compilation, packaging et portabilité ; une validation interactive sur Windows propre reste distincte.

Consulter `05-Documentation/AUDIT-FONCTIONNEL-WINDOWS-V6108.md` pour la matrice des cas d'usage, les limites de preuve et le plan de réalignement. La version publiée est déterminée par `VERSION` et `03-Sources/VERSION`, pas par les suffixes historiques des noms de modules.
