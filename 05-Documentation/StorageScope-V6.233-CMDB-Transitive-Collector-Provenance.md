# StorageScope V6.233 — Quarantaine des sources répétées dans un composant CMDB

**Auteur : Abdelhalim Talbi** · **Statut : développement ; qualification Windows native requise**

## Cause racine reproduite

Deux observations de la même source (`cmdb`, `CMDB`, espaces périphériques ignorés) pouvaient être reliées par deux identifiants différents via un collecteur intermédiaire sans être directement appariées. Le contrôle V6.228 ne détectait que les paires directes partageant un identifiant fort. La chaîne suivante était donc marquée `REVIEW_REQUIRED` à tort :

- `cmdb` : `serial=S1`
- `probe` : `serial=S1, uuid=U2`
- `CMDB` : `uuid=U2`

Le graphe relie les trois observations. La source `cmdb` apparaît deux fois dans ce composant : les preuves ne sont pas indépendantes. Ce constat ne prouve pas que les équipements sont identiques ; il impose une **quarantaine pour revue humaine**.

## Contrat fonctionnel

La réconciliation parcourt les composantes connexes du graphe d'identités fortes (`serial`, `wwn`, `uuid`) des seuls enregistrements valides. Pour chaque composante, elle détecte les sources normalisées répétées. Les indices concernés sont exposés dans `transitive_duplicate_source_indices` et dans `duplicate_source_indices`. Toute la composante est mise en quarantaine, avec action `QUARANTINE_LINKED_DUPLICATE_SOURCE_OBSERVATION` pour les paires qui n'avaient pas déjà un conflit direct plus prioritaire. Les composantes indépendantes restent `REVIEW_REQUIRED`.

Les observations invalides ne deviennent jamais des candidats. Les conflits directs d'identité et la propagation des liens invalides conservent leur priorité. Le rapport reste en lecture seule : `automatic_merges=0`, `destructive_changes=0`. La preuve `snapshot_sha256` couvre les octets exacts du snapshot.

## Validation exigée

1. `test_cmdb_transitive_source_duplicate_v6233.py` : cinq scénarios synthétiques, non-régression et intégrité du snapshot.
2. Tests historiques CMDB, notamment V6.228, V6.230, V6.231 et V6.232.
3. CI gouvernance Linux et Windows sur le commit exact.
4. CI native Windows : exécutable PyInstaller V6.233 contrôlé par `qualify_frozen_cmdb_transitive_source_v6233.py`, puis Inno Setup, installation/désinstallation, portable, SHA-256 et artefacts.

**Limites :** aucun essai physique SAN/NAS ni capture réelle d'interface. Une CI de gouvernance verte ne suffit pas à qualifier Windows. Les identifiants de provenance sont déclaratifs ; leur authenticité dépend des contrôles de collecte en amont.

## Alignement

Traçabilité des décisions et preuves (ISO/IEC/IEEE 42010), gestion des configurations et CI (ITIL 4), intégrité des données (ISO/IEC 27001 et 27040). La quarantaine n'est pas une remédiation automatique.
