# StorageScope V6.225 — Ancrage indépendant du registre anti-rejeu

**Auteur : Abdelhalim Talbi.** **Statut : développement ; Windows V6.225 non qualifié tant que sa CI native n'est pas verte.**

## Objectif et menace

Le registre SQLite V6.222 empêche la réutilisation d'un identifiant de collecte signé ; V6.224 audite ses lignes. Une restauration d'un fichier SQLite ancien mais valide reste indétectable par un audit isolé. V6.225 crée un **point de contrôle HMAC-SHA256 indépendant** qui authentifie le contenu logique complet du registre et le nombre de collectes. Une restauration plus ancienne est rejetée si le point de contrôle le plus récent reste disponible dans un domaine de protection distinct.

## Contrat d'exploitation

1. Définir `STORAGESCOPE_REPLAY_ANCHOR_KEY` à une clé **hexadécimale de 32 octets**, distribuée par un coffre sécurisé ; ne jamais la committer, journaliser ni inclure dans les archives.
2. Stocker les ancrages **dans un répertoire distinct**, idéalement un stockage immuable sauvegardé indépendamment du registre. Ne jamais restaurer ensemble un registre et son ancien ancrage.
3. Après une collecte enregistrée, émettre un **nouveau nom de fichier** avec `StorageScope.exe --storage-replay-anchor-create CHEMIN_REGISTRE CHEMIN_ANCRAGE` ; l'opération refuse les fichiers déjà existants.
4. Avant de considérer le registre fiable, exécuter `StorageScope.exe --storage-replay-anchor-check CHEMIN_REGISTRE CHEMIN_ANCRAGE_LE_PLUS_RECENT` et exiger `integrity=PASS`. Une erreur ou l'absence d'ancrage est bloquante.
5. La vérification est en lecture seule ; elle ne consomme aucun identifiant et n'écrit pas dans le registre. L'empreinte authentifie toutes les lignes triées, avec sérialisation canonique et séparation de domaine.

## Garanties et limites

- **Détecté :** restauration du registre à un état différent de l'ancrage protégé, modification d'une ligne, ajout ou retrait de lignes, clé incorrecte, ancrage absent ou altéré.
- **Non garanti :** restauration simultanée du registre et de l'ancrage, compromission de la clé, administrateur local malveillant disposant du secret, fraîcheur d'une collecte ou identité cryptographique du collecteur.
- **Risque d'interruption :** l'ancrage n'est pas mis à jour automatiquement à chaque écriture SQLite. Une collecte acceptée après émission d'un ancrage rend ce dernier obsolète jusqu'à création d'un nouvel ancrage. La vérification **échoue alors volontairement**. Une procédure opérateur de reprise est nécessaire ; ne pas désactiver le contrôle.
- **Rotation :** la rotation du secret d'ancrage n'est pas encore automatisée ; elle requiert une procédure contrôlée hors bande.
- **Compatibilité :** les registres V6.222 existants ne sont pas modifiés. Le contrôle est opt-in et n'affecte pas le calcul des risques SAN/NAS en lecture seule.

## Qualification

Neuf tests unitaires synthétiques couvrent création, vérification, non-modification, rollback, altération à cardinalité identique, nouvel ancrage versionné, clé incorrecte, séparation des répertoires, ligne invalide et CLI. Un contrôle spécifique exécute les commandes dans le **binaire Windows compilé** avant publication, puis conserve les portes PyInstaller/Inno Setup, installation/désinstallation, portable et SHA-256. Aucun test sur baie physique ni capture réelle d'interface n'est revendiqué.

## Alignement

ISO 27001/27040 : intégrité et protection des preuves ; ITIL 4 : gestion du changement et traçabilité ; ISO 42010 : décision d'architecture explicite et limites de confiance. Ce mécanisme n'est pas une certification de conformité.
