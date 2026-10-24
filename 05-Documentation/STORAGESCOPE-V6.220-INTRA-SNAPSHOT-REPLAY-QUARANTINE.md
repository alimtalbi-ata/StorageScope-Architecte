# StorageScope V6.220 — quarantaine des preuves HMAC répétées

**Auteur : Abdelhalim Talbi — 24 octobre 2026.**

## Besoin et correction

La V6.219 valide HMAC-SHA256 mais ne distingue pas une observation signée
originale de sa copie exacte. Deux copies d'un relevé ne sont pas deux preuves
indépendantes. Avec `observation_auth_policy`, la V6.220 recherche les
enveloppes HMAC **vérifiées** répétées dans un snapshot SAN/NAS, en utilisant
`(source_ref, key_id, hmac_sha256)`. Toutes les copies sont mises en quarantaine
indépendamment de leur ordre d'apparition. Les signatures invalides sont
traitées séparément par les contrôles HMAC existants.

Le moteur de risques et la cartographie de dépendances ajoutent
`replayed_path_observations` et `replayed_share_observations`. Les constats
`REPLAYED_PATH_OBSERVATION` et `REPLAYED_SHARE_OBSERVATION` empêchent de
promouvoir des copies en chemins actifs ou partages vérifiés. Le Diagnostic
Windows affiche les compteurs et les limites. Aucun secret ni digest n'est
publié dans les nouveaux rapports. Les snapshots historiques sans politique
HMAC conservent leur comportement.

## Limite de sécurité essentielle

**Il ne s'agit PAS d'une protection anti-rejeu inter-snapshots.**
Aucun registre persistant ni horloge de confiance n'est fourni ; une ancienne
observation signée unique peut toujours être réutilisée dans un nouveau
snapshot. La fraîcheur V6.216 doit être configurée explicitement. Une
protection complète nécessitera un identifiant unique signé par collecte,
un registre transactionnel persistant, une politique d'expiration et la
rotation contrôlée des clés. Deux signatures distinctes ne prouvent pas
l'indépendance physique de deux chemins SAN.

## Qualification

Tests synthétiques :
`python -m unittest discover -s 04-Tests-et-Qualification -p 'test_storage_observation_replay_v6220.py' -v`

Test du binaire PyInstaller Windows :
`python 04-Tests-et-Qualification/qualify_frozen_observation_replay_v6220.py --exe <StorageScope.exe>`.

Les tests locaux Linux ne constituent pas une qualification Windows native.
Ne déclarer installateur, désinstallation, portable ou SHA-256 vérifiés
qu'après leur exécution réelle sur le commit exact.

Aucune connexion infrastructure, écriture CMDB, remédiation ou donnée réelle.
Alignement visé : ISO/IEC/IEEE 42010, ITIL 4, ISO/IEC 27001 et ISO/IEC 27040 ;
aucune certification revendiquée.
