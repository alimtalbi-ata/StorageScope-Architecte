# StorageScope V6.226 — durcissement des ancrages anti-rejeu

**Auteur : Abdelhalim Talbi** — 25 octobre 2026.

## Défaut et cause racine

V6.225 contrôlait le HMAC du registre, mais acceptait un JSON ambigu (clés dupliquées ou sérialisation non canonique) et ne détectait ni les hardlinks ni les liens symboliques présents dans un grand-parent du chemin d'ancrage. Le risque est une indépendance de stockage supposée mais non garantie.

## Correctif

- Lecture d'un fichier ordinaire unique (nombre de liens physiques égal à 1), vérification des métadonnées du descripteur ouvert et du chemin, et `O_NOFOLLOW` lorsqu'il existe.
- Refus des liens symboliques dans tous les composants du chemin fourni.
- Comparaison octet par octet avec la représentation JSON canonique, ce qui rejette les clés dupliquées et les encodages alternatifs.
- Préservation de la commande V6.225, des ancrages valides, de la lecture seule et de l'absence d'exposition des secrets.

## Vérifications

Les cinq tests synthétiques `test_storage_replay_anchor_v6226.py` couvrent un ancrage valide, une clé JSON dupliquée, un JSON non canonique, un hardlink et un symlink dans un grand-parent. Les tests V6.225 restent actifs. `qualify_frozen_replay_anchor_v6226.py` vérifie aussi le comportement de l'exécutable PyInstaller dans la CI native Windows. Un cas non supporté par le système de fichiers est signalé **SKIPPED**, jamais PASS.

## Exploitation

Conserver le registre SQLite et l'ancrage dans des domaines de sauvegarde distincts. Stocker la clé hexadécimale de 32 octets dans `STORAGESCOPE_REPLAY_ANCHOR_KEY` via un gestionnaire de secrets. Créer des ancrages versionnés sans écraser l'ancien : `StorageScope.exe --storage-replay-anchor-create <registre> <ancrage>`. Vérifier : `StorageScope.exe --storage-replay-anchor-check <registre> <ancrage>`. Traiter tout rejet comme une anomalie de provenance.

## Limites

La détection des modifications concurrentes des composants parents n'est pas entièrement atomique sur Windows, où `O_NOFOLLOW` peut être absent. Une restauration simultanée du registre et de l'ancrage reste indétectable sans stockage externe immuable. Aucun équipement physique, capture d'interface réelle ou test UX humain n'a été utilisé. Ne déclarer Windows V6.226 qualifié qu'après succès complet du workflow natif et contrôle des artefacts.

**Référentiels :** ISO 27001/27040 (intégrité des preuves, séparation des domaines), ISO 42010 (justification d'architecture), ITIL 4 (contrôle des changements). Il ne s'agit pas d'une certification.
