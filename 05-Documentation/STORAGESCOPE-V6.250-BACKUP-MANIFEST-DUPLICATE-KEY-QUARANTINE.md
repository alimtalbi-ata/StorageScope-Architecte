# StorageScope V6.250 — rejet des clés JSON dupliquées dans les manifestes de sauvegarde

**Auteur : Abdelhalim Talbi**  
**Date : 26 octobre 2026**

## Risque traité

Le décodeur JSON standard de Python conserve silencieusement la dernière valeur lorsqu'un objet contient plusieurs fois la même clé. Dans un manifeste de sauvegarde, cette règle peut rendre ambigus le format, l'inventaire ou l'empreinte SHA-256 d'un fichier. Un contrôleur peut alors accepter une représentation différente de celle qu'un autre lecteur consomme.

Ce défaut est indépendant des 225 anomalies historiques du run Windows #39668811238. Il concerne l'intégrité de la preuve de sauvegarde, pas la compilation native.

## Correction

- Ajout d'un hook strict de paires clé/valeur qui refuse toute clé dupliquée dans chaque objet JSON, y compris les objets imbriqués.
- Le refus utilise une exception de validation traitée par verify_backup_snapshot ; le résultat reste un refus fermé (False).
- Aucun fichier de sauvegarde n'est réécrit, supprimé ou réparé pendant la vérification.
- Le nouveau test est exécuté dans la gouvernance Linux et dans la qualification native Windows.

## Régressions ajoutées

Le module test_backup_manifest_duplicate_key_quarantine_v6250.py couvre la validité d'un manifeste non ambigu, les clés format et files dupliquées au niveau supérieur, une clé sha256 dupliquée dans un objet fichier, un membre inconnu dupliqué et le raccordement aux deux workflows. Les cas négatifs utilisent de vraies chaînes JSON à doublons, pas des dictionnaires Python qui auraient déjà perdu la duplication.

La qualification de cette modification doit être fondée sur les workflows exécutés sur le HEAD exact. Les tests ciblés ne remplacent ni le build PyInstaller/Inno Setup, ni les contrôles d'installation, de désinstallation, du portable et des manifestes SHA-256.

## Gouvernance et limites

Cette mesure contribue au contrôle d'intégrité et à la réduction du risque lié aux sauvegardes (ISO 27001/27040 selon le périmètre) et à la traçabilité des décisions de conception (ISO/IEC/IEEE 42010). TOGAF, ArchiMate et ITIL 4 sont des cadres d'alignement, pas des certifications obtenues par ce correctif.

Aucune baie SAN/NAS physique, restauration de production ou interface graphique réelle n'est exercée par ces tests synthétiques. La résolution individuelle des 225 symptômes historiques reste à prouver par un rapprochement cause-racine/correctif/test.
