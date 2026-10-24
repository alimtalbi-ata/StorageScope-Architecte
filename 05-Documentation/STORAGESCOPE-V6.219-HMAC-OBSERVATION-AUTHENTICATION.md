# StorageScope V6.219 — Authentification HMAC des observations SAN/NAS

**Auteur : Abdelhalim Talbi** · 24 octobre 2026 · Branche de développement, PR draft, aucun merge automatique.

## Besoin métier et défaut corrigé

La V6.218 sait filtrer les identifiants de collecteurs déclarés, mais n'empêche pas une personne ayant accès au fichier JSON d'usurper `source_ref` ou de remplacer `state: down` par `up`. Le filtrage n'est pas une preuve d'intégrité. La V6.219 ajoute une **politique facultative** d'authentification HMAC-SHA256 par source pour les chemins SAN et les partages NAS. Si cette politique est activée, une preuve sans HMAC valide ne peut ni certifier un chemin actif ni créer une relation de partage NAS vérifiée. Les snapshots historiques sans politique restent compatibles et **ne sont pas présentés comme authentifiés**.

## Contrat de données

Le JSON d'inventaire garde `schema: storagescope.storage-topology.v1` et peut ajouter :

```json
"observation_auth_policy": {
  "schema": "storagescope.observation-auth-policy.v1",
  "source_keys": {"collector:approved": "COLLECTOR_A"}
}
```

Chaque élément de `paths` et `shares` doit porter un `source_ref` correspondant à la politique et une enveloppe `auth` :

```json
"auth": {"key_id": "COLLECTOR_A", "hmac_sha256": "<64 caractères hexadécimaux minuscules>"}
```

La clé partagée de 32 à 128 octets est provisionnée **hors du snapshot**, via la variable d'environnement `STORAGESCOPE_HMAC_KEY_COLLECTOR_A` en hexadécimal. Utiliser une clé **différente par source** ; le contrat rejette les identifiants de clé réutilisés entre sources. Ne jamais écrire les clés dans le dépôt, les ZIP, les rapports ou les journaux. Dans un environnement Windows, provisionner la variable pour le processus uniquement à l'aide d'un mécanisme sécurisé adapté ; éviter les variables persistantes non protégées.

La signature est calculée par `hmac.new(key, b"StorageScope.observation.hmac-sha256.v1\x00" + canonical_json, sha256)`, où `canonical_json` est l'objet d'observation sans la propriété `auth`, encodé UTF-8 avec `json.dumps(sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)`. Utiliser la fonction `sign_observation(record, key_id, secret)` du module `storage_observation_auth_v6219.py` dans le collecteur hors ligne. Cette fonction renvoie une copie ; elle n'écrit aucun fichier et ne modifie pas le record initial.

## Chaîne de contrôle et décisions

1. Parser un fichier JSON UTF-8 borné, sans propriétés dupliquées (contrôle V6.196).
2. Valider strictement la politique et l'association `source_ref` → `key_id`.
3. Vérifier la présence et la forme de l'enveloppe HMAC, puis la clé provisionnée hors fichier.
4. Calculer le HMAC du payload complet et comparer en temps constant avec `hmac.compare_digest`.
5. Appliquer **également** les contrôles indépendants de source autorisée (V6.218), d'horodatage (V6.215) et de fraîcheur (V6.216). Une signature correcte ne rend pas un relevé périmé acceptable.
6. En cas d'échec : constat `UNAUTHENTICATED_PATH_OBSERVATION` ou `UNAUTHENTICATED_SHARE_OBSERVATION`, relation non vérifiée, statut `INCOMPLETE` ; un doublon SAN physiquement identique et non authentifié empoisonne la signature même si un autre relevé dit `up`.
7. Reporter uniquement des **compteurs** (vérifiées, signature incorrecte, clé absente, enveloppe absente, source inconnue), sans émettre de clé ni d'identifiant de clé. Le Diagnostic Windows affiche les compteurs et le disclaimer.

## Sécurité, limites et gouvernance

- **HMAC n'est pas une signature asymétrique** : la possession d'un secret partagé prouve la connaissance du secret, pas l'identité indépendante d'une machine ni la non-répudiation. Si un collecteur est compromis, ses relevés peuvent être falsifiés.
- Les horloges et la référence de fraîcheur restent fournies par l'opérateur, non attestées. Un ancien message HMAC valide peut être rejoué dans la fenêtre autorisée. Prévoir compteur monotone, anti-rejeu transactionnel et rotation/révocation des clés dans une version future.
- Les noms de source, signatures et secrets ne sont pas reproduits dans les constats. La clé peut exister temporairement dans la mémoire du processus et son environnement ; durcir le lancement Windows en conséquence.
- Contrôle **lecture seule**, aucune connexion à des baies physiques, aucune écriture CMDB, aucune remédiation automatique, aucun accès réseau.
- TOGAF / ISO 42010 : décision d'architecture explicite et limites de confiance ; ISO 27001 / 27040 : intégrité et gestion des clés ; ITIL 4 : traçabilité des preuves d'incident ; ArchiMate : relations d'infrastructure observées, sans extrapolation applicative.

## Qualification et livraison

Tests unitaires synthétiques `test_storage_observation_auth_v6219.py` : chemin et partage signés, modification du payload, duplicat contradictoire quel que soit l'ordre, absence de clé, schéma invalide, compatibilité legacy, Unicode, date périmée, absence de fuite dans le rapport. CI gouvernance Linux/Windows exécute la suite ; CI Windows native exécute aussi `qualify_frozen_observation_auth_v6219.py` **contre l'exécutable PyInstaller**, puis conserve les gates installateur/désinstallation/portable et SHA-256. Ces gates doivent être **effectivement verts sur le commit V6.219** avant de déclarer cette version qualifiée.

Aucune capture UI réelle n'a été produite lors du développement local. Toute capture de validation future devra être issue d'une exécution effective et identifiée comme telle. Ne pas présenter le schéma conceptuel comme une capture réelle.
