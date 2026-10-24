# StorageScope V6.218 — filtrage explicite des sources d'observation SAN/NAS

**Auteur : Abdelhalim Talbi** — 24 octobre 2026. Développement cumulatif sur V6.217, sans fusion automatique.

## Besoin métier et défaut couvert

Une observation de chemin SAN `up` ou un partage NAS fourni par une origine inconnue pouvait contribuer à une relation considérée comme vérifiée. Les versions précédentes contrôlaient les identités d'équipements, la cohérence des états, les horodatages et éventuellement leur fraîcheur, **mais ne disposaient d'aucun contrôle de source déclarée**. Une donnée datée ne constitue pas une donnée authentifiée.

## Contrat de politique (optionnel)

Ajouter à la racine du snapshot `storagescope.storage-topology.v1` :

```json
"source_policy": {
  "schema": "storagescope.observation-source-policy.v1",
  "allowed_source_refs": ["collector:approved", "inventory:offline"]
}
```

Chaque observation de `paths` et `shares` doit alors comporter un `source_ref` égal à un identifiant autorisé. Le format est strict : 1 à 128 caractères ASCII `[A-Za-z0-9][A-Za-z0-9._:/-]*`, 1 à 128 identifiants uniques dans la politique. Toute liste vide, entrée dupliquée, valeur non textuelle ou champ inconnu provoque un rejet explicite du snapshot. Aucun secret, URL contenant des identifiants ni jeton ne doit figurer dans `source_ref`.

En présence de la politique, une observation sans `source_ref`, malformée ou hors liste est **mise en quarantaine**. Pour les chemins SAN, l'incertitude contamine la même signature physique `(host, storage, fabric, port)` même si une autre observation prétend `up`. Pour les partages NAS, une source non admise ne peut créer une relation vérifiée. Le rapport de risques produit `UNTRUSTED_PATH_SOURCE` ou `UNTRUSTED_SHARE_SOURCE`, `assessment=INCOMPLETE` et aucune écriture CMDB. Le rapport de dépendances inclut `source_evaluation` avec compteurs `allowed/missing/invalid/unlisted` et `authentication=NOT_AUTHENTICATED`. L'interface de diagnostic affiche ces compteurs et la réserve explicite.

**Compatibilité :** sans `source_policy`, les snapshots historiques continuent à fonctionner et `source_evaluation=null`. Il ne faut **pas** interpréter cette compatibilité comme une preuve de confiance. Une politique active ne vérifie ni signature cryptographique, ni identité réseau, ni horloge de collecte : elle n'est qu'une liste de sources déclarées par l'opérateur. L'authentification réelle des collecteurs, la signature des snapshots et le chaînage des preuves constituent des travaux futurs distincts.

## Qualification et sécurité

Tests synthétiques `test_storage_source_allowlist_v6218.py` : acceptation explicite, rejet des sources inconnues/absentes/invalides, ordre indépendant de la quarantaine SAN, préservation des relations NAS sûres, validation bornée, compatibilité sans politique, déterminisme, absence de mutation, confidentialité des noms de source dans les constats. CI gouvernance Linux/Windows : exécuter ces tests sans désactiver les contrôles antérieurs. CI Windows native : exécuter le scénario V6.218 **sur le binaire PyInstaller**, puis seulement qualifier l'installateur Inno Setup, la désinstallation et le portable.

Ne pas déclarer Windows qualifié avant le résultat natif et les artefacts SHA-256 de la version exacte. Aucune capture réelle de l'interface ni essai sur baies physiques n'est disponible à la création de ce document. Aucun accès réseau ni écriture sur une infrastructure de production n'est effectué.

**Référentiels :** ISO/IEC/IEEE 42010 (hypothèses et traçabilité de preuves), ISO 27001/27040 (intégrité/provenance de l'inventaire de stockage), ITIL 4 (qualité des données de configuration), TOGAF/ArchiMate (relations d'infrastructure explicitement observées, non déduites).
