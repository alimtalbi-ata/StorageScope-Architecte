# Critères de déploiement Windows autonome

Auteur : Abdelhalim Talbi.

## Objectif
Installer ou lancer StorageScope sur un **autre ordinateur Windows x64**
sans dépôt Git, sans code source et sans installer Python, PyInstaller ou Inno Setup.

## Livrables
1. `StorageScope-Setup-vX.Y.exe` : installateur Windows autonome.
2. `StorageScope-Portable-vX.Y-win-x64.zip` : archive contenant `StorageScope.exe`.

## Contrôles automatisés
- Construction native sur Windows avec les scripts existants.
- Installation silencieuse, vérification de version, désinstallation.
- Extraction portable dans un répertoire temporaire distinct du dépôt.
- Exécution depuis un répertoire externe, avec `PYTHONPATH` vidé.
- Vérification du manifeste et des empreintes via `verify-binary-delivery.py`.
- Artefacts GitHub Actions publiés uniquement si les contrôles passent.

## Limites
Le runner de compilation contient Python et des outils de développement.
Ce test ne prouve donc **pas** encore l'absence de dépendance sur une machine
Windows totalement vierge. Une validation supplémentaire dans une VM Windows
propre, sans Python ni accès au code source, reste **obligatoire** avant
qualification finale. Vérifier également antivirus, SmartScreen, signatures,
Windows 10/11 x64 et toutes les fonctionnalités de l'interface.

**Statut** : procédure et workflow ajoutés ; aucun binaire déclaré qualifié
avant résultat GitHub Actions et essai sur PC Windows indépendant.
