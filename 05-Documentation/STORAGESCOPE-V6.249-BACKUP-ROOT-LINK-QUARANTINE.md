# StorageScope V6.249 — protection des racines de sauvegarde

**Auteur : Abdelhalim Talbi**  
**Date : 26 octobre 2026**

## Défaut corrigé

La vérification de sauvegarde contrôlait les liens symboliques du manifeste et des fichiers contenus dans un snapshot, mais ne vérifiait pas que le répertoire du snapshot lui-même — ni ses répertoires ancêtres — était atteint par un chemin réel. Un chemin de répertoire présenté comme local pouvait donc pointer vers une autre arborescence via un lien symbolique. Sur Windows, une jonction NTFS doit être traitée de la même façon.

Ce défaut ne modifie pas le contenu d’une sauvegarde et n’était pas démontré comme cause des 225 anomalies du run historique #39668811238. Il s’agit d’un correctif de sécurité indépendant sur le contrôle de restauration.

## Correction

- Vérification de chaque composant du chemin absolu avant toute lecture du manifeste.
- Refus des liens symboliques et des jonctions Windows lorsque `Path.is_junction()` est disponible.
- Inspection de tous les composants du chemin absolu avant normalisation de `..`, afin qu'une séquence lien/parent ne masque pas le composant lié.
- Normalisation des segments seulement après validation de la frontière, avant la lecture du manifeste.
- Rejet explicite d’un chemin qui n’est pas un répertoire.
- Aucune écriture, suppression ou réparation automatique des données utilisateur : la vérification reste en lecture seule.

## Régressions

Le fichier `04-Tests-et-Qualification/test_backup_root_link_quarantine_v6249.py` couvre :
- l’acceptation d’un snapshot normal avec empreinte valide ;
- le refus d’un lien sur la racine avant l’ouverture du manifeste ;
- le refus d’un ancêtre symbolique avant l’ouverture du manifeste ;
- le refus d’un chemin qui contient un lien suivi de `..`, même lorsque sa destination normalisée est un snapshot valide ;
- la détection déterministe d’un composant de type jonction Windows ;
- le refus d’un fichier transmis comme racine.

Les tests d’intégration de liens peuvent signaler un skip uniquement si l’environnement refuse la création de liens. Le workflow natif Windows doit s’exécuter sur le HEAD exact avant de revendiquer la livraison.

## Architecture et gouvernance

La protection renforce l’intégrité de la chaîne sauvegarde/restauration et la gestion des risques techniques (ISO 27001/27040 selon le périmètre), ainsi que la traçabilité des décisions de conception (ISO/IEC/IEEE 42010). TOGAF/ArchiMate et ITIL 4 restent des cadres d’alignement ; aucune certification n’est revendiquée.

**Limites :** aucune restauration sur données de production ni aucun test sur baie SAN/NAS physique n’est effectué par cette qualification. La correction ne ferme pas la traçabilité individuelle des 225 anomalies historiques.
