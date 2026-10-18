# Point d'entrée unique: bootstrap outils, tests, EXE, installateur, verification.
# Auteur: Abdelhalim Talbi
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$releaseVersion = (Get-Content (Join-Path $PSScriptRoot 'VERSION') -Raw).Trim()
if ($releaseVersion -notmatch '^\d+\.\d+$') { throw 'Invalid VERSION format' }
$logDir = Join-Path $PSScriptRoot 'build-logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logFile = Join-Path $logDir ("build-v${releaseVersion}-{0}.log" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
Start-Transcript -Path $logFile -ErrorAction Stop | Out-Null
try {
function Invoke-Checked([string]$Exe, [string[]]$Arguments) {
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Exe failed (exit $LASTEXITCODE): $($Arguments -join ' ')" }
}
function Find-Python {
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        & $py.Source -3.12 -c 'import sys; assert sys.version_info >= (3,12)'
        if ($LASTEXITCODE -eq 0) { return @{ Executable=$py.Source; Args=@('-3.12') } }
    }
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) {
        & $python.Source -c 'import sys; assert sys.version_info >= (3,12)'
        if ($LASTEXITCODE -eq 0) { return @{ Executable=$python.Source; Args=@() } }
    }
    return $null
}
function Find-ISCC {
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    )
    foreach ($candidate in $candidates) { if (Test-Path $candidate) { return $candidate } }
    return $null
}
$python = Find-Python
if (-not $python) {
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) { throw 'Python 3.12 absent et winget indisponible. Installer App Installer/winget ou Python 3.12.' }
    Invoke-Checked 'winget.exe' @('install','--id','Python.Python.3.12','--exact','--silent','--accept-package-agreements','--accept-source-agreements')
    $python = Find-Python
    if (-not $python) {
        $candidates = @(Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe", "$env:ProgramFiles\Python312\python.exe" -ErrorAction SilentlyContinue)
        if ($candidates.Count) { $python = @{ Executable=$candidates[0].FullName; Args=@() } }
    }
    if (-not $python) { throw 'Python installé mais introuvable. Relancer le CMD dans une nouvelle session.' }
}
# Clean stale artifacts so the release cannot accidentally package an old binary.
foreach ($artifact in @('dist\StorageScope.exe', 'dist\StorageScope-UpgradeGate.exe', ("installer\StorageScope-Setup-v{0}.exe" -f $releaseVersion))) {
    if (Test-Path $artifact) { Remove-Item $artifact -Force }
}
# Explicit preflight for consistent versioning and required build inputs.
Invoke-Checked $python.Executable ($python.Args + @('verify-windows-build.py'))
$venv = Join-Path $PSScriptRoot '.build-venv'
if (-not (Test-Path "$venv\Scripts\python.exe")) { Invoke-Checked $python.Executable ($python.Args + @('-m','venv',$venv)) }
 $builder = "$venv\Scripts\python.exe"
Invoke-Checked $builder @('verify-windows-build.py')
Invoke-Checked $builder @('-m','pip','install','--disable-pip-version-check','--requirement','requirements-build.txt')
Invoke-Checked $builder @('-m','unittest','discover','-s','.','-p','test_*.py','-q')
Invoke-Checked $builder @('-m','PyInstaller','--clean','--noconfirm','StorageScope.spec')
# Independent console-mode gate: no Python required on the target PC.
Invoke-Checked $builder @('-m','PyInstaller','--clean','--noconfirm','--onefile','--console','--name','StorageScope-UpgradeGate','upgrade_gate_v581.py')
if (-not (Test-Path 'dist\StorageScope-UpgradeGate.exe')) { throw 'Upgrade gate EXE absent' }
if (-not (Test-Path 'dist\StorageScope.exe')) { throw 'EXE absent apres compilation' }
Invoke-Checked "$PSScriptRoot\dist\StorageScope.exe" @('--self-test')
# Windowed PyInstaller binaries do not have a reliable stdout handle.
# Request version via an explicit file and verify the process exit code.
$versionProbe = Join-Path $PSScriptRoot 'dist\version-probe.txt'
if (Test-Path $versionProbe) { Remove-Item $versionProbe -Force }
Invoke-Checked "$PSScriptRoot\dist\StorageScope.exe" @('--version-file', $versionProbe)
if (-not (Test-Path $versionProbe)) { throw 'EXE version probe not created' }
$reportedVersion = (Get-Content -LiteralPath $versionProbe -Raw).Trim()
Remove-Item $versionProbe -Force
if ($reportedVersion -ne $releaseVersion) { throw "Version EXE inattendue: $reportedVersion" }
$iscc = Find-ISCC
if (-not $iscc) {
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) { throw 'Inno Setup absent et winget indisponible.' }
    Invoke-Checked 'winget.exe' @('install','--id','JRSoftware.InnoSetup','--exact','--silent','--accept-package-agreements','--accept-source-agreements')
     $iscc = Find-ISCC
    if (-not $iscc) { throw 'Inno Setup installé mais ISCC.exe introuvable. Relancer le CMD dans une nouvelle session.' }
}
Invoke-Checked $iscc @('StorageScope.iss')
# Fail closed if the installer is stale or empty.
$expectedVersion = $releaseVersion
$setup = Join-Path $PSScriptRoot ("installer\StorageScope-Setup-v{0}.exe" -f $expectedVersion)
if (-not (Test-Path $setup)) { throw 'Installateur non produit pour la version attendue' }
# Require nonempty artifacts and produce machine-readable release evidence.
$binary = Join-Path $PSScriptRoot 'dist\StorageScope.exe'
$gateBinary = Join-Path $PSScriptRoot 'dist\StorageScope-UpgradeGate.exe'
foreach ($artifact in @($binary, $gateBinary, $setup)) {
    if ((Get-Item -LiteralPath $artifact).Length -lt 1024) { throw "Artefact vide ou anormalement petit: $artifact" }
}
$manifest = @{
    version = $expectedVersion
    generated_utc = (Get-Date).ToUniversalTime().ToString('o')
    artifacts = @(
        foreach ($artifact in @($binary, $gateBinary, $setup)) {
            $item = Get-Item -LiteralPath $artifact
            @{ filename = $item.Name; bytes = $item.Length; sha256 = (Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash }
        }
    )
}
$manifestPath = Join-Path $PSScriptRoot ("installer\release-manifest-v{0}.json" -f $releaseVersion)
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Invoke-Checked $builder @('verify-installer-release.py', '--installer', $setup, '--manifest', $manifestPath, '--version', $releaseVersion)
# Portable distribution: a single PyInstaller onefile EXE, no separate Python runtime.
$portableDir = Join-Path $PSScriptRoot 'portable'
# Remove stale portable artifacts before packaging; never ship leftovers from a prior build.
if (Test-Path $portableDir) { Remove-Item -LiteralPath $portableDir -Recurse -Force }
New-Item -ItemType Directory -Path $portableDir -Force | Out-Null
$portableExe = Join-Path $portableDir 'StorageScope.exe'
Copy-Item -LiteralPath $binary -Destination $portableExe -Force
if ((Get-FileHash -LiteralPath $portableExe -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash) { throw 'Portable binary hash mismatch' }
$portableManifest = @{ version=$expectedVersion; author='Abdelhalim Talbi'; format='onefile'; executable='StorageScope.exe'; sha256=(Get-FileHash -LiteralPath $portableExe -Algorithm SHA256).Hash; bytes=(Get-Item -LiteralPath $portableExe).Length }
$portableManifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $portableDir ("portable-manifest-v{0}.json" -f $releaseVersion)) -Encoding UTF8
# Deliver a verifiable portable ZIP, not just a loose EXE.
$portableReadme = Join-Path $portableDir 'LIRE-AVANT-UTILISATION.txt'
@"
StorageScope v$releaseVersion - Windows x64 portable
Auteur : Abdelhalim Talbi
Lancer StorageScope.exe sans installer Python.
Donnees utilisateur : %LOCALAPPDATA%\StorageScope (hors du dossier portable).
Portable signifie executable autonome, PAS donnees portables.
Ne pas supprimer ce dossier de donnees lors du nettoyage de l'application.
"@ | Set-Content -LiteralPath $portableReadme -Encoding UTF8
$portableZip = Join-Path $portableDir ("StorageScope-Portable-v{0}-win-x64.zip" -f $releaseVersion)
if (Test-Path $portableZip) { Remove-Item -LiteralPath $portableZip -Force }
Compress-Archive -LiteralPath @($portableExe,$portableReadme,(Join-Path $portableDir ("portable-manifest-v{0}.json" -f $releaseVersion))) -DestinationPath $portableZip -CompressionLevel Optimal
if ((Get-Item -LiteralPath $portableZip).Length -lt 1024) { throw 'Archive portable invalide' }
$zipHash = (Get-FileHash -LiteralPath $portableZip -Algorithm SHA256).Hash
@{ version=$releaseVersion; archive=(Split-Path $portableZip -Leaf); bytes=(Get-Item $portableZip).Length; sha256=$zipHash } |
  ConvertTo-Json | Set-Content -LiteralPath (Join-Path $portableDir ("portable-zip-sha256-v{0}.json" -f $releaseVersion)) -Encoding UTF8
# Verify ZIP payload and digest using Python standard library before release.
Invoke-Checked $builder @('verify-portable-release.py', '--zip', $portableZip, '--manifest', (Join-Path $portableDir ("portable-manifest-v{0}.json" -f $releaseVersion)), '--version', $releaseVersion)
Write-Host "PORTABLE PRET: $portableExe"
Write-Host "INSTALLATEUR PRET: $setup"
Write-Host "MANIFESTE: $manifestPath"
} catch {
    Write-Error "ECHEC BUILD: $_" -ErrorAction Continue
    throw
} finally {
    Stop-Transcript | Out-Null
}
