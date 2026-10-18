# StorageScope v6.44 — Qualification de la chaîne Windows

Auteur : Abdelhalim Talbi

## Défauts observés dans v6.43
- Version de l'application Python restée à 6.38, alors que le manifeste indiquait 6.43.
- Workflow CI resté à 6.11, avec chemins d'exécution incompatibles avec l'arborescence cumulative.
- build-all-windows.ps1 absent du staging alors qu'exigé par verify-windows-build.py.
- Le vérificateur imposait un ancien contrat de version codé en dur.
- Journaux de compilation supprimés avec le répertoire temporaire après une compilation réussie.

## Correctifs v6.44
- Alignement version application, Inno Setup et manifeste à 6.44.
- Contrôle dynamique des versions et préflight sans version figée.
- Workflow GitHub Actions adapté à l'arborescence cumulative et aux sorties de compilation.
- Copie de build-all-windows.ps1 dans le staging.
- Conservation des build-logs après succès.
- Cinq tests ciblés de cohérence de release.

## Exécution Windows
Extraire le ZIP, puis exécuter Construire-StorageScope.cmd à la racine.
Ensuite : powershell -NoProfile -ExecutionPolicy Bypass -File 02-Compilation-Windows\qualify-native-windows.ps1
Collecter 02-Compilation-Windows\build-logs et windows-qualification-report.json.

## Limites et preuves
Tests de contrat Python exécutés sous Linux ; vérification offline du staging exécutée sous Linux.
Compilation PyInstaller, Inno Setup, installation, UI et désinstallation Windows NON exécutées.
Aucune capture Windows réelle disponible ; aucune capture fictive présentée comme réelle.
