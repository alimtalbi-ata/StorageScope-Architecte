StorageScope v6.43 — Qualification Windows
Auteur : Abdelhalim Talbi

Objectif : fiabiliser le vérificateur natif, sans prétendre à une exécution Windows.

Corrections : recherche des artefacts par chemins exacts dans dist et installer; contrôle SHA-256; option SkipInstaller excluant le contrôle du manifeste de l’installateur; refus de la qualification native sur un système non Windows lorsque PowerShell 7 est utilisé.

Exécution sur Windows : Construire-StorageScope.cmd puis powershell -NoProfile -ExecutionPolicy Bypass -File 02-Compilation-Windows\qualify-native-windows.ps1

Résultats : six tests de contrat Python exécutés sous Linux. Build Windows, GUI, installation et désinstallation : non exécutés.

Architecture : archive -> préparation Windows -> PyInstaller -> Inno Setup -> manifestes -> qualification native -> rapport JSON.

Limites : les contrôles statiques ne prouvent ni le lancement graphique ni l’installation. Les captures réelles Windows ne sont pas disponibles.
