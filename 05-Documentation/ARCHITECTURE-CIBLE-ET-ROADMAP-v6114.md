# StorageScope — Architecture cible et dette technique (v6.114 → v6.120)

Auteur : Abdelhalim Talbi. État : plan d'évolution, non déclaration de fonctionnalités livrées.

## Constats vérifiés
- Le dépôt compile actuellement une application v6.108. L'archive cumulative v6.113 n'est pas encore importée dans la branche d'intégration.
- La compilation PyInstaller et Inno Setup ainsi que le test Windows d'installation/désinstallation et d'exécution portable hors dépôt ont réussi sur GitHub Actions (commit 58312d8).
- Les tests de pagination v6.114 passent. La suite historique complète comporte des échecs : elle ne doit pas être présentée comme qualifiée.
- La validation sur une machine Windows vierge sans Python reste distincte de GitHub Actions.

## Principes d'architecture
1. **Compatibilité et conservation des données** : aucun changement de schéma sans migration versionnée, transaction, sauvegarde vérifiée et test de restauration.
2. **UI mince** : widgets Tkinter et contrôleurs n'effectuent ni requêtes SQL brutes ni accès constructeur ; ils appellent des services.
3. **Domaine indépendant** : inventaire canonique (CI, ports, volumes, relations), topologie et diagnostics sans dépendance Tkinter.
4. **Connecteurs isolés** : API/CLI/collecteurs derrière interfaces typées ; erreurs et provenance explicites, aucune découverte inventée.
5. **Persistance transactionnelle** : SQLite avec clés étrangères, WAL lorsque pertinent, opérations idempotentes, contraintes d'unicité et journal d'audit.
6. **Sécurité** : sauvegarde avant mise à jour, secrets hors dépôt, accès minimum, aucune restauration destructive implicite.
7. **Observabilité** : durée, volume, erreurs, identifiant de corrélation, traces de qualification et indicateurs mesurables.
8. **Packaging reproductible** : scripts Windows uniques, versions concordantes, empreintes SHA256, installateur et portable qualifiés.

## Modules cibles (migration incrémentale)
- `storagescope/domain/` : modèles, identifiants, validation, relations.
- `storagescope/application/` : cas d'usage, recherche, pagination, export, diagnostics.
- `storagescope/infrastructure/` : SQLite, sauvegardes, connecteurs, journaux.
- `storagescope/ui/` : vues, contrôleurs et adaptateurs Tkinter.
- `storagescope/compat/` : façades de transition pour l'ancien code.
- `tests/unit`, `tests/integration`, `tests/windows` : suites différenciées.

**Ne pas déplacer les modules en bloc.** Introduire une façade compatible et migrer une fonctionnalité à la fois, avec tests d'équivalence et comparaison des exports.

## Priorités de livraison
| Version | Priorité | Livrable | Critère de sortie |
|---|---|---|---|
| v6.114 | P0 | Alignement code v6.113, CI Windows, tests ciblés | version manifestes/EXE identique ; installer/portable fonctionnels |
| v6.115 | P0 | Services SQLite et sauvegarde | crash/reprise, migration et restauration vérifiées |
| v6.116 | P0 | Inventaire canonique et recherche | unicité, provenance, filtres et pagination bornée |
| v6.117 | P1 | Topologie SAN/NAS/stockage | relations cohérentes, performance sur grand graphe mesurée |
| v6.118 | P1 | HLD/LLD, gouvernance, exports | traçabilité décisions/risques et rapports reproductibles |
| v6.119 | P2 | Connecteurs constructeurs | contrats versionnés, erreurs explicites, fixtures anonymisées |
| v6.120 | P1 | Ergonomie et stabilisation | tests E2E, accessibilité, release candidate documentée |

## Mesures avant optimisation
Capturer temps de démarrage, temps de recherche (p50/p95), mémoire résidente, nombre de requêtes SQL, temps de rendu de 1k/10k/100k relations et taux d'erreur. Fixer des objectifs seulement après baseline mesurée. Ne pas annoncer de gains non mesurés.

## Qualification et preuves
Les captures d'écran doivent provenir d'une exécution réelle ; les maquettes doivent être étiquetées. Les guides Word/PDF doivent être mis à jour dans le ZIP cumulatif à chaque version. Les tests historiques en échec doivent figurer dans le rapport avec causes et plan de résorption.