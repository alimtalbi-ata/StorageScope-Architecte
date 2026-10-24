# StorageScope V6.221 — rotation contrôlée des clés HMAC SAN/NAS

**Auteur : Abdelhalim Talbi — 24 octobre 2026.**

## Objectif

Migrer progressivement la clé partagée HMAC-SHA256 d'un collecteur SAN/NAS sans promouvoir une observation signée par une clé retirée. Aucun accès infrastructure, aucune écriture CMDB et aucune remédiation automatique.

## Contrat et configuration

La politique `storagescope.observation-auth-policy.v1` reste compatible : une source correspond à un identifiant de clé. La politique `storagescope.observation-auth-policy.v2` associe chaque source à une liste **d'un ou deux identifiants**. Maximum 64 sources ; identifiants uniques entre toutes les sources et les slots de rotation. Toute clé dupliquée, champ inconnu ou politique malformée est rejeté avant évaluation.

Exemple fictif sans secret :

```json
{
  "observation_auth_policy": {
    "schema": "storagescope.observation-auth-policy.v2",
    "source_keys": {"collector:approved": ["COLLECTOR_NEW", "COLLECTOR_OLD"]}
  }
}
```

L'opérateur provisionne les secrets dans `STORAGESCOPE_HMAC_KEY_COLLECTOR_NEW` et `STORAGESCOPE_HMAC_KEY_COLLECTOR_OLD` via un environnement sécurisé, jamais dans les snapshots, commits ou rapports. Le collecteur signe avec la nouvelle clé. Pendant la fenêtre de recouvrement, les deux clés sont vérifiables. Après transition, retirer `COLLECTOR_OLD` de la politique **et supprimer son secret de l'environnement**. Un ancien HMAC devient `INVALID_AUTH`, même si son secret reste disponible.

## Protection contre le downgrade

Définir `STORAGESCOPE_REQUIRE_OBSERVATION_AUTH_V2=1` pour refuser toute politique v1 ou absente. Conserver `STORAGESCOPE_REQUIRE_OBSERVATION_AUTH=1` pour imposer la présence d'une politique. La politique embarquée dans un snapshot n'est pas authentifiée : sécuriser aussi le canal de distribution des politiques et révoquer effectivement les secrets retirés.

## Résultats et sécurité

Le moteur de risques et la cartographie des dépendances vérifient la clé déclarée dans chaque enveloppe HMAC. Une clé retirée, une signature altérée ou un secret indisponible empêche de promouvoir un chemin SAN ou un partage NAS comme fiable. Les résumés ajoutent `rotation_active_sources` sans divulguer les identifiants de clés ni les secrets. La quarantaine anti-rejeu intra-snapshot V6.220 reste active. **Aucune protection anti-rejeu entre snapshots n'est encore fournie.** L'HMAC prouve la possession d'un secret partagé, pas l'identité indépendante du collecteur ni la fiabilité de son horloge.

## Qualification

Tests synthétiques : `python -m unittest discover -s 04-Tests-et-Qualification -p 'test_storage_key_rotation_v6221.py' -v`.

CI Windows native : `python 04-Tests-et-Qualification/qualify_frozen_key_rotation_v6221.py --exe <StorageScope.exe>` après compilation PyInstaller. Cas contrôlés : ancienne/nouvelle clé, révocation, downgrade interdit et quota falsifié. Les tests locaux Linux ne qualifient ni l'exécutable Windows, ni Inno Setup, ni l'installation, ni le portable.

Références de conception : ISO/IEC/IEEE 42010, ISO/IEC 27001, ISO/IEC 27040, ITIL 4 ; aucune certification revendiquée.

## Suite

V6.222 : registre transactionnel anti-rejeu inter-snapshots, identifiant de collecte signé, atomicité et rollback, sans écriture implicite pendant une analyse.
