# StorageScope V6.215 — Horodatage et provenance SAN/NAS

**Auteur : Abdelhalim Talbi — 24 octobre 2026.** Changement proposé en PR draft. Aucun test ni artefact n'est déclaré réussi avant l'exécution correspondante.

## Problème métier

Les chemins SAN et partages NAS issus de collectes différentes pouvaient porter un champ `observed_at` invalide (heure locale sans fuseau, date impossible, texte libre) tout en étant considérés comme des observations fiables. Une autre observation `up` du même chemin pouvait masquer cette incohérence. Un horodatage valide dans un inventaire ne prouve cependant **ni** l'heure de collecte réelle, **ni** la fraîcheur, **ni** l'authenticité de la source.

## Contrat de données

Le schéma d'entrée reste `storagescope.storage-topology.v1`. Les objets de `paths[]` et `shares[]` acceptent le champ **facultatif** `observed_at` au format ISO 8601 avec fuseau explicite : `2026-10-24T12:00:00+02:00` ou `2026-10-24T10:00:00Z`. Les fractions de seconde sont limitées à six chiffres. Les valeurs sans fuseau, impossibles, booléennes, nulles ou non conformes sont invalides.

- **Absent** : l'ancien inventaire demeure exploitable, mais aucune fraîcheur n'est inférée.
- **Valide** : normalisation UTC sans modifier le snapshot ; le dernier instant **parsé** n'est pas présenté comme une preuve d'authenticité.
- **Explicitement invalide** : quarantaine de l'observation dans le moteur de dépendances ; les autres chemins et partages indépendants demeurent visibles. Un chemin de même signature physique est empoisonné dans les deux ordres d'observation.
- **Risque** : les nouveaux constats `INVALID_PATH_TIMESTAMP` et `INVALID_SHARE_TIMESTAMP` rendent le risque `INCOMPLETE`, sans réconciliation ni remédiation automatique.
- **Rapport** : `dependency_impact.observation_times` expose `valid_observations`, `missing_observations`, `invalid_observations`, `latest_parsed_utc` et `freshness=NOT_ASSESSED`. Les enregistrements non objets sont inclus dans les observations sans horodatage.
- **Diagnostic Windows** : compteurs et dernier instant daté, avec avertissement explicite « Fraîcheur : NON ÉVALUÉE ».

### Exemple synthétique (non exécuté sur équipement)

```json
{
  "schema": "storagescope.storage-topology.v1",
  "assets": [
    {"id": "h1", "kind": "host"},
    {"id": "a1", "kind": "storage_array", "used_gib": 20, "total_gib": 100}
  ],
  "paths": [
    {"host_id": "h1", "storage_id": "a1", "fabric": "A", "state": "up", "observed_at": "2026-10-24T12:00:00+02:00"},
    {"host_id": "h1", "storage_id": "a1", "fabric": "B", "state": "up", "observed_at": "2026-10-24T12:00:00"}
  ],
  "shares": []
}
```

Résultat attendu : `verified_host_relationships=1`, `unverified_host_relationships=1`, `mixed_evidence_host_relationships=1`, `assessment=INCOMPLETE`, `latest_parsed_utc=2026-10-24T10:00:00Z`. Ce résultat est un **contrat de test**, pas une preuve d'exécution.

## Reproduction et contrôles

```sh
python -m unittest discover -s 04-Tests-et-Qualification -p 'test_storage_observation_time_v6215.py' -v
python -m unittest discover -s 04-Tests-et-Qualification -p 'test_storage_dependency*.py' -v
python -m unittest discover -s 04-Tests-et-Qualification -p 'test_storage_path_risk_v6194.py' -v
```

La CI gouvernance exécute les nouveaux tests sur Linux **et** Windows, avec contrôle du code retour. La CI Windows native vérifie l'export produit par l'exécutable PyInstaller, puis poursuit les contrôles installateur Inno Setup, désinstallation, portable et empreintes SHA-256. Seul un résultat réussi sur le HEAD exact autorise à annoncer une qualification Windows automatisée.

## Architecture et normes

- **ISO/IEC/IEEE 42010** : provenance et limites explicites de la vue de dépendances.
- **TOGAF / ArchiMate** : distinction entre relations observées, incertaines et non établies ; aucun service applicatif inféré.
- **ITIL 4** : les observations douteuses sont signalées avant toute réconciliation CMDB.
- **ISO 27001 / 27040** : validation des métadonnées, quarantaine fail-closed, aucune action destructive.

## Limites et preuves

Aucune capture réelle de l'interface Windows ni validation UX humaine n'est fournie. Aucun horodatage de collecte, certificat d'origine, signature de télémétrie ou vérification de fraîcheur n'est inventé. Les dates de l'exemple sont **synthétiques**. La version interne du produit reste 6.108 tant qu'une migration de version distincte n'est pas qualifiée.
