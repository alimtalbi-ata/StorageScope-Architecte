# StorageScope v6.46

## Objectif
Corriger la vérification de version d’un exécutable PyInstaller sans console Windows.

## Défaut identifié
L’ancienne commande --version lisait stdout, indisponible ou non fiable pour une application GUI compilée avec console=False.

## Correctif
L’option --version-file CHEMIN écrit la version dans un fichier UTF-8. Les scripts de compilation et de qualification lisent ce fichier, comparent la version attendue et suppriment le fichier temporaire.

## Architecture
Source Python → PyInstaller GUI → EXE → --version-file → fichier temporaire → contrôle PowerShell → manifeste de livraison.

## Procédure
Lancer Construire-StorageScope.cmd, puis 02-Compilation-Windows/qualify-native-windows.ps1. Conserver les journaux et le rapport JSON.

## Résultats attendus (non exécutés sur Windows)
Exemple fictif : version-probe.txt contient 6.46 ; le contrôle affiche PASS lorsque la version concorde.

## Limites de qualification
Aucune compilation Windows native, aucun essai d’installation, aucune capture réelle UI n’ont été effectués. Les tests Linux ne prouvent pas la compatibilité Windows.