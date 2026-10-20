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
