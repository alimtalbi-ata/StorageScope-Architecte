StorageScope v6.41 - Qualification Windows et contrats de livraison

Auteur : Abdelhalim Talbi

Base : v6.40. Cette version corrige les contrats de version de compilation et de qualification.

Correction 1 : la version du build est lue depuis 07-Manifestes/VERSION ; les noms des artefacts attendus sont calcules dynamiquement.

Correction 2 : le controle de l executable installe compare strictement sa version a celle du manifeste.

Qualification reelle : quatre tests de contrat executes sous Linux avec succes. Integrite ZIP verifiee.

Limites : aucune compilation Windows, installation, capture graphique ni regression complete executee.

Procedure : extraire le ZIP sous Windows, lancer Construire-StorageScope.cmd, puis 02-Compilation-Windows/qualify-native-windows.ps1.

Prochaine etape : collecter le rapport windows-qualification-report.json et les journaux de build natifs pour corriger les erreurs observees.
