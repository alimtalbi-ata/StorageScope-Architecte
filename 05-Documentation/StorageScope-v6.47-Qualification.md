# StorageScope v6.47 - Qualification Windows

## Objectif
Fiabiliser le transfert du workflow CI vers le staging et garantir une preuve de qualification.

## Defaut corrige
Le staging supposait que le workflow GitHub Actions se trouvait dans 03-Sources/.github, alors que la livraison contient egalement un workflow a la racine. La v6.47 privilegie le workflow racine et utilise un repli explicite.

## Controle de retour
Un ancien LASTEXITCODE pouvait provoquer une erreur trompeuse apres un appel PowerShell. Le pipeline verifie desormais le statut PowerShell de cet appel.

## Evidence Windows
Le workflow exige la presence du rapport JSON de qualification avant de declarer la phase reussie.

## Architecture
ZIP cumulatif -> preflight -> staging isole -> tests Python -> PyInstaller -> Inno Setup -> qualification native -> rapport JSON.

## Procedure
Sous Windows, executer Construire-StorageScope.cmd, puis 02-Compilation-Windows/qualify-native-windows.ps1. Conserver les logs et le rapport JSON.

## Limites
Aucun build Windows, test installation, capture UI reelle ni recette graphique n a ete execute dans cet environnement Linux. Les scenarios documentes sont des exemples, non des preuves.

## Auteur
Abdelhalim Talbi