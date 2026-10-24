; Compile with Inno Setup 6 on Windows after build-windows.ps1
#define AppVersion "6.108"
[Setup]
AppId={{A6B4A820-846E-497A-89D0-89BE0F617E63}
AppName=StorageScope
AppVersion={#AppVersion}
AppPublisher=Abdelhalim Talbi
DefaultDirName={localappdata}\Programs\StorageScope
DefaultGroupName=StorageScope
OutputDir=installer
OutputBaseFilename=StorageScope-Setup-v{#AppVersion}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
UninstallDisplayIcon={app}\StorageScope.exe
; Les donnees sont dans {localappdata}\StorageScope, hors du dossier programme.
; Ne jamais les effacer a la desinstallation.
[Files]
Source: "dist\StorageScope-UpgradeGate.exe"; Flags: dontcopy
; Ship the same validated gate in the installed application as well as the pre-upgrade temporary extraction.
Source: "dist\StorageScope-UpgradeGate.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\StorageScope.exe"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\StorageScope"; Filename: "{app}\StorageScope.exe"
Name: "{autodesktop}\StorageScope"; Filename: "{app}\StorageScope.exe"; Tasks: desktopicon
[Tasks]
Name: desktopicon; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"
[Run]
Filename: "{app}\StorageScope.exe"; Description: "Démarrer StorageScope"; Flags: nowait postinstall skipifsilent

[Code]
// Run before any program files are replaced. A failed gate blocks the upgrade.
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  DataDir, BackupDir, GateExe, Args: String;
  ExitCode: Integer;
begin
  Result := '';
  DataDir := ExpandConstant('{localappdata}\StorageScope');
  if not DirExists(DataDir) then
    Exit;
  BackupDir := ExpandConstant('{localappdata}\StorageScope-Upgrade-Backups');
  try
    ExtractTemporaryFile('StorageScope-UpgradeGate.exe');
    GateExe := ExpandConstant('{tmp}\StorageScope-UpgradeGate.exe');
    Args := '--data-dir "' + DataDir + '" --backup-dir "' + BackupDir + '"';
    if not Exec(GateExe, Args, '', SW_HIDE, ewWaitUntilTerminated, ExitCode) then
      Result := 'Impossible de lancer le controle de sauvegarde pre-mise-a-jour.'
    else if ExitCode <> 0 then
      Result := 'Sauvegarde pre-mise-a-jour non valide. Installation interrompue.';
  except
    Result := 'Echec du controle de sauvegarde. Installation interrompue.';
  end;
end;
