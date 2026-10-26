# StorageScope V6.252 — refus des constantes numériques JSON non standard dans les manifestes de sauvegarde

**Auteur : Abdelhalim Talbi**  
**Date : 26 octobre 2026**  
**Branche :** `feature/storagescope-v6.252-backup-json-nonfinite-quarantine-20261026`  
**Base :** V6.250 — protection contre les clés JSON dupliquées

## Risque et cause

Le décodeur `json.loads` de Python accepte par défaut les jetons `NaN`, `Infinity` et `-Infinity`, bien qu'ils ne fassent pas partie de la grammaire JSON standard. V6.250 avait supprimé l'ambiguïté des clés dupliquées, mais un manifeste pouvait toujours contenir l'un de ces jetons dans un champ d'extension ignoré par le lecteur. Un consommateur strict pourrait interpréter le même document différemment.

## Correction

- Ajout de `_reject_non_finite_json_constant`, passé à `json.loads` via `parse_constant`.
- Toute apparition de `NaN`, `Infinity` ou `-Infinity`, y compris dans un objet imbriqué ou un champ d'extension, déclenche un refus fermé de `verify_backup_snapshot`.
- Les nombres et littéraux JSON standards restent acceptés.
- La validation demeure en lecture seule : le manifeste n'est jamais réécrit et le contenu des fichiers de sauvegarde n'est pas modifié.

## Tests et contrôles

`04-Tests-et-Qualification/test_backup_json_nonfinite_quarantine_v6252.py` utilise des manifestes JSON bruts pour vérifier les trois jetons non standard, l'intégrité inchangée du contenu et l'acceptation de valeurs JSON standards dans les métadonnées d'extension. Le test est raccordé à la gouvernance Linux et au workflow de qualification native Windows.

La qualification doit être lue à partir des workflows exécutés sur le HEAD exact. Le succès des tests ciblés ne remplace pas les contrôles du build PyInstaller/Inno Setup, l'installation/désinstallation, le portable et les empreintes SHA-256.

## Alignement et limites

Ce contrôle soutient l'intégrité des preuves de sauvegarde (ISO 27001/27040 selon le périmètre) et la traçabilité de l'architecture décrite selon ISO/IEC/IEEE 42010. TOGAF, ArchiMate et ITIL 4 peuvent guider l'alignement global ; aucun label de conformité ni certification n'est revendiqué.

Aucun test de baie SAN/NAS physique, aucune restauration de production, aucune capture réelle d'interface et aucune résolution complète des 225 anomalies historiques (#39668811238) ne sont revendiqués par ce correctif.
