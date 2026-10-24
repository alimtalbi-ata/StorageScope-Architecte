# StorageScope V6.224 — Validation exhaustive des métadonnées du registre anti-rejeu

**Auteur : Abdelhalim Talbi** — 24 octobre 2026 — proposition sur branche dédiée, sans fusion automatique.

## Défaut métier et impact

L'audit V6.223 validait uniquement `MIN(accepted_utc)` et `MAX(accepted_utc)`.
Or SQLite compare les horodatages TEXT lexicalement. Une ligne intermédiaire
avec un horodatage invalide, ou une identité de collecte UUID falsifiée,
pouvait être présente tout en produisant `integrity=PASS`. Cela ne modifiait
pas directement les observations SAN/NAS, mais créait un faux positif de
qualité des preuves d'audit.

## Correctif V6.224

L'audit parcourt **toutes** les lignes de `collection_seen` via un curseur
SQLite en lecture seule, sans charger le registre complet en mémoire. Chaque
ligne doit avoir : `source_ref` non vide, `collection_id` UUIDv4 canonique,
`observation_count` entier strictement positif et `accepted_utc` interprétable
comme une date avec fuseau UTC. Toute anomalie provoque un refus explicite,
sans divulguer les valeurs sensibles. Le résultat d'audit reste agrégé.

Les contrôles existants de schéma, clé primaire, intégrité SQLite, lecture seule,
absence de création automatique et fermeture des handles sont conservés.
L'opération a une complexité temporelle O(nombre de collections) et doit être
planifiée hors pics de charge sur les très gros registres.

## Qualification et preuve attendue

- Tests unitaires : horodatage malformé **au milieu de trois lignes**, UUID
  falsifié, source vide, compteur négatif injecté par fixture SQLite ; audit
  inchangé pour un registre sain.
- Tests de non-régression V6.222/V6.223 et suite historique.
- CI Windows native : script `qualify_frozen_replay_audit_v6224.py` contre
  `StorageScope.exe` compilé, vérification du rejet, de SHA-256 inchangé et de
  la libération du handle de fichier.
- PyInstaller, Inno Setup, installation, désinstallation et portable restent
  des gates obligatoires **distincts**. Aucun résultat Windows V6.224 ne peut
  être annoncé avant la réussite de ces étapes sur le commit exact.

## Limites de sécurité

Ce contrôle **ne prouve pas** l'absence de rollback du fichier SQLite ni
l'authenticité cryptographique du registre. Un administrateur local peut
remplacer le registre par une ancienne copie structurellement valide.
La protection contre ce scénario nécessite un ancrage monotone hors du périmètre
de restauration et une stratégie de rotation des clés.

## Référentiels

ISO 27001 / ISO 27040 : intégrité et traçabilité des preuves de stockage.
ISO 42010 : définition explicite des garanties et limites du composant.
ITIL 4 : diagnostic exploitable et contrôles de changement.
Aucune certification n'est revendiquée.

**Captures réelles UI : non réalisées. Essais SAN/NAS physiques : non réalisés.**
