# StorageScope V6.216 — politique explicite de fraîcheur SAN/NAS

**Auteur : Abdelhalim Talbi** · 24 octobre 2026 · évolution cumulative V6.215 → V6.216.

## Objectif

La validation ISO 8601 de V6.215 ne prouvait pas qu'un chemin SAN ou un partage NAS était récent. V6.216 ajoute une fenêtre d'âge explicitement fournie par l'architecte, sans lire l'heure système, le réseau ou la CMDB. Les observations périmées, futures, invalides ou non datées ne peuvent plus certifier une dépendance lorsqu'une politique est présente.

## Contrat JSON — exemple entièrement synthétique

```json
{
  "schema": "storagescope.storage-topology.v1",
  "freshness_policy": {
    "schema": "storagescope.observation-freshness-policy.v1",
    "reference_time": "2026-10-24T10:00:00Z",
    "max_age_seconds": 120,
    "max_future_skew_seconds": 5
  },
  "assets": [], "paths": [], "shares": []
}
```

`reference_time` doit être ISO 8601 avec fuseau ; `max_age_seconds` est un entier strict de 1 à 31 536 000, `max_future_skew_seconds` un entier strict de 0 à 3600 (défaut 0). Les booléens, champs inconnus et références invalides sont refusés. Les bornes sont inclusives. La politique est facultative pour les anciens snapshots : en son absence, le comportement V6.215 reste inchangé et la fraîcheur n'est pas évaluée.

## Sémantique fail-closed

- **FRESH** : dans la fenêtre, mais horloge et origine non authentifiées.
- **STALE** : âge supérieur au maximum ; chemin ou partage non vérifié.
- **FUTURE** : date au-delà de la tolérance ; chemin ou partage non vérifié.
- **MISSING** : absence de date sous politique explicite ; non vérifié.
- **INVALID** : date malformée, toujours refusée.

Une observation SAN non fiable contamine toute la signature hôte/baie/fabric/port, indépendamment de l'ordre des enregistrements. Une autre fabric saine demeure observée, mais ne masque pas les preuves mixtes et le résultat reste **INCOMPLETE**. Les partages NAS non fiables sont exclus du nombre vérifié et comptés comme observations non résolues. Aucun changement automatique CMDB.

## Architecture et restitution

Snapshot hors ligne → parseur JSON borné → validation de la politique → risques SAN/NAS → graphe de dépendances → rapport JSON et Diagnostic Windows. Le rapport ajoute `freshness_evaluation` avec référence UTC, seuils, compteurs et `trust=UNAUTHENTICATED_INPUT_CLOCK`. La valeur V6.215 `observation_times.freshness=NOT_ASSESSED` reste descriptive de la seule validation syntaxique et ne remplace pas l'évaluation de politique.

ISO/IEC/IEEE 42010 : limites et hypothèses d'architecture explicites ; ISO 27001/27040 : maîtrise du risque d'inventaire ; ITIL 4 : qualité de l'information d'actifs. Ce module ne vérifie **ni signature du collecteur, ni NTP, ni identité source, ni exhaustivité CMDB**. Une référence falsifiée peut induire une conclusion trompeuse : contrôle humain et provenance attestée restent nécessaires.

## Tests et limites

`python -m unittest discover -s 04-Tests-et-Qualification -p 'test_storage_observation_freshness_v6216.py' -v` : neuf tests synthétiques ciblés (frontières, stale/future/missing, ordre, compatibilité, export et sécurité). CI gouvernance Linux/Windows et test fonctionnel de l'exécutable Windows intégrés. Ne déclarer la qualification Windows qu'après vérification du build natif, de l'installateur, du portable et des artefacts. Captures UI réelles et validation UX humaine absentes. Aucun secret, équipement réel, écriture de production ni fusion automatique.
