# StorageScope V6.211 — SAN path evidence: mixed states and impact review

**Auteur : Abdelhalim Talbi** · 24 octobre 2026 · Statut : proposition, PR draft.

## Problème et cause racine

Le calcul `uncertain_pairs -= verified_pairs` dans `storage_dependency_impact_v6199.py` supprimait l'indication de chemins douteux dès qu'un autre chemin du même couple hôte/baie était vérifié. Une liaison SAN pouvait donc être affichée comme entièrement vérifiée malgré un chemin de fabric A contradictoire et un chemin de fabric B actif. Cette suppression masquait le risque dans le rapport de dépendances et le tableau Diagnostic Windows.

## Correctif

- Conserver séparément les observations **vérifiées** et **non vérifiées** par couple hôte/baie. Les deux catégories peuvent coexister ; ne pas additionner leurs compteurs comme des hôtes distincts.
- Introduire `mixed_evidence_host_relationships` et, pour chaque équipement, `mixed_evidence_host_ids`.
- Lorsque des chemins non vérifiés existent, conserver `assessment=INCOMPLETE` même si un autre fabric est actif.
- Afficher le total des preuves mixtes et les hôtes concernés dans Diagnostic Windows.
- Aucun changement automatique de CMDB, aucune remédiation, aucune suppression de données.

## Exemple synthétique

| Hôte | Baie | Fabric | Port | Observations |
| --- | --- | --- | --- | --- |
| h1 | a1 | A | p1 | up, down (contradictoire) |
| h1 | a1 | B | p2 | up (vérifié) |

Résultat attendu : `verified_host_relationships=1`, `unverified_host_relationships=1`, `mixed_evidence_host_relationships=1`, `assessment=INCOMPLETE`. L'identifiant `h1` apparaît à la fois dans les ensembles vérifiés et non vérifiés ; ce n'est pas un doublon de comptage.

## Qualification et limites

Cinq tests nouveaux couvrent : coexistence d'états contradictoires, isolement d'une autre baie saine, état inconnu, invariance à l'ordre, projection Diagnostic Windows. Un test historique a été corrigé car son ancienne attente masquait explicitement le défaut. **Exécution locale Linux : 5/5 nouveaux tests PASS et 13/13 tests de dépendances PASS**. Cette preuve ne vaut pas qualification Windows native ; le workflow Windows comprend un nouveau contrôle de l'exécutable PyInstaller. Les résultats de ce workflow et les artefacts ne sont valides qu'après exécution GitHub Actions effective.

Les autres tests historiques du dépôt nécessitent leur environnement de qualification prévu ; un lancement brut sous Linux n'est pas assimilable à la suite Windows complète. Les captures d'écran Windows réelles et les essais UX manuels ne sont pas disponibles dans ce cycle.

## Traçabilité architecture et exploitation

- **ISO/IEC/IEEE 42010** : hypothèses et limites de preuve explicites dans la vue de dépendances.
- **ArchiMate** : ne pas inférer une relation de service à partir d'une simple liaison hôte/baie.
- **TOGAF** : conserver la séparation entre constat, décision d'architecture et remédiation.
- **ITIL 4** : soutenir l'analyse d'impact et la gestion des risques d'incident sans prétendre connaître tous les services dépendants.
- **ISO 27001 / 27040** : intégrité de l'évidence, lecture seule, absence de promotion automatique d'un état incertain en état sain.

## Suites

Valider le workflow Windows natif et ses artefacts, puis enrichir la cartographie des dépendances vers les services applicatifs avec provenance, dates d'observation et limites de couverture. Aucune fusion automatique dans `main`.
