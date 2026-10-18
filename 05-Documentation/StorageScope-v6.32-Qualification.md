# StorageScope v6.32 — Build Windows et qualification

Auteur : Abdelhalim Talbi

## Problèmes constatés dans v6.31
Le build utilisait encore la version 6.17 alors que l'application annonçait 6.29, et le répertoire de compilation était séparé des sources. Cette divergence pouvait provoquer des échecs et des artefacts périmés.

## Changements
- Version source et Inno Setup harmonisée en 6.32.
- Orchestrateur de build en répertoire isolé, puis export des résultats.
- Le script `build-engine-windows.ps1` conserve la qualification existante et ne doit pas être considéré comme validé sur Windows sans exécution.

## Exécution réelle / preuves
Les contrôles Python et l'intégrité ZIP ont été effectués sous Linux. Aucune compilation native Windows ni capture graphique réelle n'est disponible.

## Commande Windows attendue
`02-Compilation-Windows\Construire-StorageScope.cmd`

## Critères de réception
EXE démarrable, `--version` = 6.32, `--self-test` réussi, installateur v6.32 produit, installation et désinstallation vérifiées sur machine Windows propre.

## Limitations
L'orchestrateur et les scripts historiques doivent être validés en CI Windows ; des dépendances ou ressources supplémentaires peuvent encore être nécessaires.
