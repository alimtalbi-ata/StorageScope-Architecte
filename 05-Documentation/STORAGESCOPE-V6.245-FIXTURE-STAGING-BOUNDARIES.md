# StorageScope V6.245 — frontières sûres des fixtures historiques

**Auteur : Abdelhalim Talbi**  
**Branche : feature/storagescope-v6.245-fixture-boundaries-20261026**  
**Base : V6.244 — staging sûr des workflows actifs**

## Constat supplémentaire

V6.244 protège les workflows actifs, mais deux chemins de bord restaient :
1. une racine source symbolique pendante pouvait être traitée comme un répertoire absent, puisque exists() était évalué avant is_symlink() ;
2. une racine source et une destination identiques ou imbriquées pouvaient faire entrer la destination dans l'arbre parcouru ;
3. le workflow historique v5.89 utilisait encore copy2 après un contrôle de destination. Un fichier différent créé entre ce contrôle et la copie pouvait être tronqué/remplacé, et une destination symbolique n'était pas refusée explicitement.

## Correction V6.245

- Refuse d'abord une source symbolique, y compris pendante.
- Résout les deux racines avant toute création, puis refuse l'égalité et tout chevauchement d'arborescences.
- Réutilise un même mécanisme de staging pour les fichiers actifs et le workflow historique v5.89 : copie temporaire, vérification octet par octet, promotion par lien dur qui ne remplace pas une destination préexistante, et nettoyage du temporaire.
- Refuse les collisions divergentes, destinations symboliques et chemins parents de fixture qui ne sont pas des répertoires.
- Ajoute des tests de non-chevauchement, de source symbolique pendante, de conflit préexistant et de création concurrente au point de promotion.
- Exécute la nouvelle suite ciblée dans la CI de gouvernance Linux et Windows.

## Tests

Fichier : 04-Tests-et-Qualification/test_historical_workflow_staging_boundaries_v6245.py

Commande :
python -m unittest discover -s 04-Tests-et-Qualification -p 'test_historical_workflow_staging_boundaries_v6245.py' -v

Les tests utilisent une primitive no-overwrite réelle (os.link) ; la course est injectée au point d'appel et vérifie que les octets ajoutés par l'autre acteur restent intacts. Les tests de symlink simulent le prédicat de plateforme pour éviter de dépendre des privilèges de création de liens Windows.

## Portée et limites

La correction ferme un risque de mutation silencieuse dans le runner de qualification ; elle ne supprime pas les 225 anomalies de la référence #39668811238 (958 tests, 52 failures, 173 errors) et ne prouve pas encore la correspondance individuelle de chaque diagnostic à un correctif.

La garantie no-overwrite porte sur le nom du fichier au moment de sa promotion. Elle ne remplace pas une isolation OS complète contre un acteur capable de remplacer simultanément des répertoires parents ; le runner s'exécute dans un checkout CI contrôlé. Aucun test sur baies SAN/NAS physiques, aucune écriture CMDB, aucune capture UI réelle et aucune certification ISO ne sont revendiqués.

Référentiels : la cohérence des preuves relève de la gouvernance des changements et des actifs (ITIL 4, ISO/IEC 27001/27040) et de la spécification des hypothèses de qualification (ISO/IEC/IEEE 42010). TOGAF et ArchiMate peuvent référencer ce contrôle dans la vue du cycle de vie et du processus d'ingénierie ; aucune conformité certifiée n'est affirmée.

Aucune modification de main, aucune fusion automatique et aucun déploiement opérationnel.
