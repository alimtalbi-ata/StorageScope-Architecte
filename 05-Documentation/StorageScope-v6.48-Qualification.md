# StorageScope v6.48 — Qualification installateur Windows

Auteur : Abdelhalim Talbi

## Évolution
La CI Windows exécute désormais un test d'installation et désinstallation silencieuses, dans un répertoire temporaire isolé, après la compilation et la qualification des exécutables.

## Parcours du test
1. Vérification de la présence de l'installateur correspondant à VERSION.
2. Installation Inno Setup avec /VERYSILENT /SUPPRESSMSGBOXES /NORESTART et /DIR.
3. Contrôle de la présence de StorageScope.exe et de sa version via --version-file.
4. Désinstallation avec unins000.exe et vérification de la disparition du binaire.
5. Production du rapport windows-installer-smoke-report.json.

## Limites
Aucune compilation ni installation Windows n'a été exécutée dans l'environnement Linux de création de l'archive. Le test CI doit être exécuté sur Windows avant toute revendication de qualification native. Les données applicatives utilisateur ne sont jamais supprimées par ce test. Une recette GUI interactive reste nécessaire.

## Commandes Windows
Construire-StorageScope.cmd

powershell -NoProfile -ExecutionPolicy Bypass -File "02-Compilation-Windows\qualify-native-windows.ps1"

powershell -NoProfile -ExecutionPolicy Bypass -File "02-Compilation-Windows\qualify-installer-smoke-windows.ps1"

## Diagramme logique (schéma documentaire, non capture réelle)
Sources -> Staging -> PyInstaller -> Inno Setup -> Vérification binaire -> Installation isolée -> Vérification version -> Désinstallation -> Rapport JSON.
