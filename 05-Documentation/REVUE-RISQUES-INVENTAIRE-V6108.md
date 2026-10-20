# Revue des risques de réconciliation d'inventaire — v6.108

Auteur : Abdelhalim Talbi

## Objectif métier

Éviter qu'un rapprochement d'équipements fondé sur un seul identifiant (serial, WWN ou UUID) masque une contradiction matérielle. La réconciliation demeure strictement en lecture seule et chaque rapprochement requiert une revue humaine.

## Règles

- HIGH : un identifiant matériel non vide est contradictoire entre deux candidats.
- MEDIUM : deux candidats viennent de la même source ou présentent des attributs divergents.
- LOW : identité compatible entre sources distinctes, sans divergence détectée.
- Aucun niveau n'autorise de fusion automatique.

## Intégration et limites

Le module `03-Sources/inventory_review_risk_v620.py` enrichit le résultat de `inventory_reconcile_v619.reconcile` avec `identity_disagreements`, `same_source`, `risk`, `review_required` et `high_risk_count`.

Les tests `test_inventory_review_risk_v620.py` couvrent la contradiction WWN, le doublon interne et la correspondance compatible. Le workflow `diagnostic-regression.yml` les exécute.

**Intégration :** le service `governance_service.assess` enrichit désormais les candidats avec le risque, les contradictions et l'origine ; `governance_desktop.explain_candidate` transmet ces données à la couche de présentation. Les tests d'intégration sont ajoutés à la CI. **Limite :** l'affichage graphique effectif, les actions de revue et la recette Windows interactive doivent encore être qualifiés ; cette évolution ne prouve pas à elle seule un parcours UI complet.

## Suites prioritaires

Intégrer le risque dans l'interface de revue, vérifier les scénarios multi-vendeurs et les identifiants manquants, mesurer les performances sur de grands inventaires, puis documenter les preuves d'exécution Windows. Les résultats de CI doivent être consultés avant publication de la release.

## Contrôle du registre de décisions

La fonction `review_registry_v622.decide` rejette désormais les candidats explicitement bloqués par la politique d'identité, ceux sans identité stable et ceux classés `HIGH` ou portant des contradictions matérielles. Ce contrôle s'applique aussi aux appels CLI, indépendamment de l'interface graphique. Le test `test_cli_cannot_approve_blocked_identity` vérifie le refus de décision. Une vérification de bout en bout du registre et de l'interface reste nécessaire.

## Qualification du cycle de décision

Le test `test_authorized_decision_is_durable_and_auditable` vérifie une approbation admissible, la création durable du registre SQLite, la validité de la chaîne d'audit, le refus d'une seconde décision et la conservation de l'intégrité après ce refus. Le test `test_cli_cannot_approve_blocked_identity` confirme en outre que le rejet d'une décision interdite ne crée pas de fichier SQLite. Ces scénarios sont exécutés par le workflow de régression ; leur succès ne remplace pas une recette interactive de l'application Windows.

## Historique et preuve d'intégrité

Les tests de la console de gouvernance couvrent désormais la consultation d'un historique d'audit en lecture seule, son filtrage par clé de candidat et la restitution de l'empreinte complète. Un scénario de falsification SQLite modifie volontairement un réviseur et confirme que la vérification de chaîne échoue et que la consultation est refusée. Les tests restent exécutés hors interface graphique réelle : une capture et une recette interactive Windows sont encore nécessaires.

## Affichage de la revue humaine

Le tableau Tkinter de gouvernance comporte désormais une colonne `risk` entre les équipements et leur statut d'éligibilité, afin de rendre les risques HIGH/MEDIUM/LOW visibles sans ouvrir chaque fiche. Les contradictions détaillées restent disponibles dans le panneau d'explication. Cette modification de source n'est pas une preuve de capture réelle ou de recette interactive Windows.
