# Tests natifs Windows: installation silencieuse, mise a jour idempotente et desinstallation.
# Executer apres build-all-windows.ps1, uniquement sur une VM Windows jetable.
# Auteur: Abdelhalim Talbi
param([string]$Version = ((Get-Content (Join-Path (Split-Path -Parent $PSScriptRoot) '07-Manifestes/VERSION') -Raw).Trim()))
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$setup = Join-Path $PSScriptRoot ("installer\StorageScope-Setup-v{0}.exe" -f $Version)
$install = Join-Path $env:LOCALAPPDATA 'Programs\StorageScope'
$data = Join-Path $env:LOCALAPPDATA 'StorageScope'
$sentinel = Join-Path $data 'installation-qualification-preserve.txt'
if (-not (Test-Path -LiteralPath $setup)) { throw "Installateur absent: $setup" }
if (Test-Path -LiteralPath $install) { throw "Refus: dossier d'installation preexistant: $install. Utiliser une VM vierge." }
if (Test-Path -LiteralPath $data) { throw "Refus: donnees utilisateur preexistantes: $data. Utiliser une VM vierge." }
function Invoke-Installer([string]$Exe, [string[]]$Args) {
    $p = Start-Process -FilePath $Exe -ArgumentList $Args -Wait -PassThru
    if ($p.ExitCode -ne 0) { throw "Echec code $($p.ExitCode): $Exe" }
}
$installed = $false
try {
    Invoke-Installer $setup @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-')
    $binary = Join-Path $install 'StorageScope.exe'
    if (-not (Test-Path -LiteralPath $binary)) { throw 'Application absente apres installation' }
    Invoke-Installer $binary @('--self-test')
    if (-not (Test-Path -LiteralPath (Join-Path $install 'StorageScope-UpgradeGate.exe') -PathType Leaf)) { throw 'Upgrade gate absent apres installation' }
    & (Join-Path $PSScriptRoot 'qualifier-executable-windows.ps1') -Executable $binary -ExpectedVersion $Version
    New-Item -ItemType Directory -Path $data -Force | Out-Null
    Set-Content -LiteralPath $sentinel -Value 'PRESERVE-V578' -Encoding ASCII
    $installed = $true
    # Reinstallation de la meme version = test de mise a jour sans purge des donnees.
    Invoke-Installer $setup @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-')
    if ((Get-Content -LiteralPath $sentinel -Raw).Trim() -ne 'PRESERVE-V578') { throw 'Perte des donnees apres mise a jour' }
    $uninstall = Join-Path $install 'unins000.exe'
    if (-not (Test-Path -LiteralPath $uninstall)) { throw 'Desinstalleur absent' }
    Invoke-Installer $uninstall @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART')
    $installed = $false
    if (Test-Path -LiteralPath $binary) { throw 'Binaire encore present apres desinstallation' }
    if ((Get-Content -LiteralPath $sentinel -Raw).Trim() -ne 'PRESERVE-V578') { throw 'Donnees effacees apres desinstallation' }
    Write-Host 'PASS: installation, self-test, mise a jour, desinstallation, preservation des donnees.'
} finally {
    # Ne jamais supprimer automatiquement les donnees utilisateur ou les fichiers d'installation.
    if ($installed) { Write-Warning 'Installation potentiellement presente: inspection manuelle requise.' }
}
