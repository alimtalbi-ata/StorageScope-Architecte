StorageScope v6.45 — Guide de qualification

Auteur : Abdelhalim Talbi

Correction du bootstrap Windows

Le preflight v6.44 refusait toute machine sans Python, alors que le moteur est chargé de l’installer via winget. La v6.45 remplace ce blocage par un avertissement explicite.

Conservation des preuves

En cas d’échec, le staging est conservé et les journaux disponibles sont copiés dans failed-build-logs. En cas de réussite, les journaux restent dans build-logs.

Procédure de recette Windows

1. Extraire le ZIP. 2. Exécuter Construire-StorageScope.cmd. 3. Vérifier les artefacts et le manifeste. 4. Exécuter qualify-native-windows.ps1. 5. Installer, lancer et désinstaller sur machine de test.

Limites et preuves

Les tests de contrat sont exécutés sous Linux. Aucun build natif, aucune installation et aucune capture d’écran Windows réelle ne sont attestés.