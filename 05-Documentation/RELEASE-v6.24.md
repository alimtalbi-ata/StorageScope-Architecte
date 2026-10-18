StorageScope v6.24 — Architecture et qualification

Auteur : Abdelhalim Talbi

Périmètre : intégration du moteur qualité/réconciliation avec identités stables de validation.

Flux : inventaire JSON → qualité + rapprochements → résolution des IDs → candidats éligibles → registre de validation (appel séparé).

La logique métier reste non destructive. Aucun rapprochement n’est appliqué automatiquement.

Un candidat sans identifiants stables distincts est bloqué. Les preuves de rapprochement restent explicites.

Tests nouveaux : six tests unitaires réussis sous Linux.

Limites : pas de recette globale, pas de benchmark de performance, pas de compilation Windows, pas de capture UI réelle.

Les anciens modules sont conservés tant que leurs consommateurs ne sont pas migrés.

Prochaines étapes : API unifiée, adaptation du rapport HTML, registre transactionnel et tests end-to-end.