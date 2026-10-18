# StorageScope v6.50: staged, clean, single-command Windows build.
# Auteur: Abdelhalim Talbi
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$source = Join-Path $root '03-Sources'
$releaseVersion = (Get-Content (Join-Path $root '07-Manifestes/VERSION') -Raw).Trim()
# Fail early: never spend time compiling when binary publication is unresolved.
$binaryVersionDir = Join-Path (Join-Path $root 'binary') ('v' + $releaseVersion)
if (Test-Path -LiteralPath $binaryVersionDir) { throw "Version deja publiee dans binary: $binaryVersionDir" }
$binaryStagePending = Join-Path $root '.binary-staging'
if (Test-Path -LiteralPath $binaryStagePending) { throw "Publication binary interrompue: $binaryStagePending. Examiner avant nouvelle compilation." }
if ($releaseVersion -notmatch '^\d+\.\d+$') { throw 'Version du manifeste invalide' }
if (-not (Test-Path (Join-Path $source 'storagescope_windows.py'))) { throw 'Application source missing' }
& (Join-Path $PSScriptRoot 'preflight.ps1')
if (-not $?) { throw 'Preflight failed' }
# Crash-recovery gate: never overwrite old artifacts when a prior promotion was interrupted.
# The backup is deliberately preserved for operator-assisted recovery.
$unfinishedBackup = Join-Path $PSScriptRoot '.publish-backup'
if (Test-Path -LiteralPath $unfinishedBackup) {
  throw "Publication interrompue detectee: $unfinishedBackup. Restaurer manuellement avant nouvelle compilation."
}
$unfinishedJournal = Join-Path $PSScriptRoot '.publish-pending'
if (Test-Path -LiteralPath $unfinishedJournal) {
  throw "Publication en attente non resolue: $unfinishedJournal. Examiner les preuves et sauvegardes avant toute compilation."
}
# Never destroy a previous failed build without explicit operator intervention.
$binaryStage = Join-Path $root '.binary-staging'
if (Test-Path -LiteralPath $binaryStage) { throw "Publication binary non resolue: $binaryStage" }
$binaryTarget = Join-Path (Join-Path $root 'binary') ('v' + $releaseVersion)
if (Test-Path -LiteralPath $binaryTarget) { throw "Version deja publiee: $binaryTarget" }
$stage = Join-Path $PSScriptRoot '.build-stage'
if (Test-Path -LiteralPath $stage) { throw "Ancien repertoire de compilation a examiner: $stage" }
New-Item -ItemType Directory -Path $stage | Out-Null
try {
  Copy-Item (Join-Path $source '*') $stage -Recurse -Force
  Copy-Item (Join-Path $root '07-Manifestes/VERSION') (Join-Path $stage 'VERSION') -Force
  Copy-Item (Join-Path $root '04-Tests-et-Qualification/test_*.py') $stage -Force
  # Copy auxiliary test fixtures only when needed by the selected suite.
  Copy-Item (Join-Path $PSScriptRoot 'Construire-StorageScope.cmd') $stage -Force
  Copy-Item (Join-Path $PSScriptRoot 'qualifier-installation-windows.ps1') $stage -Force
  Copy-Item (Join-Path $PSScriptRoot 'qualifier-executable-windows.ps1') $stage -Force
  # Native qualification suite is staged as a unit to prevent missing helper scripts.
  Get-ChildItem -LiteralPath $PSScriptRoot -Filter 'qualifier-*-windows.ps1' -File | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $stage -Force }
  New-Item -ItemType Directory -Path (Join-Path $stage '.github/workflows') -Force | Out-Null
  $workflowSource = Join-Path $root '.github/workflows/windows-build.yml'
  if (-not (Test-Path $workflowSource)) { $workflowSource = Join-Path $source '.github/workflows/windows-build.yml' }
  if (-not (Test-Path $workflowSource)) { throw 'Windows CI workflow missing from release sources' }
  Copy-Item -LiteralPath $workflowSource (Join-Path $stage '.github/workflows/windows-build.yml') -Force
  # Explicit required build inputs, without recursive copying of the staging directory.
  foreach ($name in @('build-all-windows.ps1','build-engine-windows.ps1','StorageScope.spec','StorageScope.iss','requirements-build.txt','verify-windows-build.py','verify-portable-release.py','verify-installer-release.py','verify-binary-delivery.py','publish-transaction.py','qualify-native-windows.ps1','qualify-installer-smoke-windows.ps1','qualify-portable-smoke-windows.ps1')) {
    Copy-Item (Join-Path $PSScriptRoot $name) (Join-Path $stage $name) -Force
  }
  # Stage the complete source tree and required tests; reject missing prerequisites.
  foreach ($required in @('StorageScope.spec','StorageScope.iss','build-all-windows.ps1','build-engine-windows.ps1','verify-windows-build.py','verify-portable-release.py','verify-installer-release.py','verify-binary-delivery.py','publish-transaction.py','requirements-build.txt','qualify-native-windows.ps1','qualify-installer-smoke-windows.ps1','qualify-portable-smoke-windows.ps1','Construire-StorageScope.cmd','qualifier-installation-windows.ps1','qualifier-executable-windows.ps1','qualifier-mise-a-jour-windows.ps1','qualifier-interruption-windows.ps1','qualifier-echec-installateur-windows.ps1','.github/workflows/windows-build.yml')) { if (-not (Test-Path (Join-Path $stage $required))) { throw "Missing staged input: $required" } }
  # Reject accidental recursive staging and stale artifacts.
  if (Test-Path (Join-Path $stage '.build-stage')) { throw 'Recursive stage detected' }
  Push-Location $stage
  try {
    & (Join-Path $stage 'build-engine-windows.ps1')
    if (-not $?) { throw 'Build engine failed' }
      } finally { Pop-Location }
  foreach ($requiredOutput in @('dist/StorageScope.exe','dist/StorageScope-UpgradeGate.exe',"installer/StorageScope-Setup-v$releaseVersion.exe","installer/release-manifest-v$releaseVersion.json","portable/StorageScope-Portable-v$releaseVersion-win-x64.zip")) { if (-not (Test-Path (Join-Path $stage $requiredOutput))) { throw "Missing build output: $requiredOutput" } }
  # Validate all release payloads before publishing any of them.
  $publishRoot = Join-Path $PSScriptRoot '.publish-pending'
  if (Test-Path -LiteralPath $publishRoot) { throw "Publication precedente non resolue: $publishRoot. Utiliser --recover avant de relancer." }
  New-Item -ItemType Directory -Path $publishRoot | Out-Null
  try {
    foreach ($dir in @('dist','installer','portable','build-logs')) {
      $from = Join-Path $stage $dir
      if (Test-Path $from) { Copy-Item -LiteralPath $from -Destination (Join-Path $publishRoot $dir) -Recurse -Force }
    }
    foreach ($relative in @('dist/StorageScope.exe','dist/StorageScope-UpgradeGate.exe',"installer/StorageScope-Setup-v$releaseVersion.exe","installer/release-manifest-v$releaseVersion.json","portable/StorageScope-Portable-v$releaseVersion-win-x64.zip")) {
      $original = Join-Path $stage $relative
      $copied = Join-Path $publishRoot $relative
      if (-not (Test-Path -LiteralPath $copied)) { throw "Publication incomplete: $relative" }
      if ((Get-FileHash -LiteralPath $original -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $copied -Algorithm SHA256).Hash) { throw "Publication alteree: $relative" }
    }
    # Tested transaction publisher: eight deterministic move-failure injection points.
    # Uses the same Python runtime already required for the PyInstaller build.
    & python (Join-Path $PSScriptRoot 'publish-transaction.py') --root $PSScriptRoot --pending $publishRoot
    if ($LASTEXITCODE -ne 0) { throw "Transactional publication failed: $LASTEXITCODE" }

  } finally {
    # Do not erase transaction evidence on failure. Recovery must be explicit.
    if (Test-Path -LiteralPath $publishRoot) { Write-Warning "Publication en attente conservee: $publishRoot" }
  }
} catch {
  # Copy logs to stable path even when staging fails; keep full stage for forensics.
  $failedLogs = Join-Path $stage 'build-logs'
  if (Test-Path $failedLogs) {
    $diagnostics = Join-Path $PSScriptRoot 'failed-build-logs'
    New-Item -ItemType Directory -Path $diagnostics -Force | Out-Null
    Copy-Item (Join-Path $failedLogs '*') $diagnostics -Force -ErrorAction SilentlyContinue
  }
  Write-Error ('Build failed; diagnostic stage retained at ' + $stage)
  throw
}

# Release delivery folder: never advertise binaries before a successful native build.
$binaryRoot = Join-Path $root 'binary'
$binaryStage = Join-Path $root '.binary-staging'
if (Test-Path -LiteralPath $binaryStage) { throw "Publication binary en attente: $binaryStage" }
New-Item -ItemType Directory -Path $binaryStage -Force | Out-Null
try {
  $outputs = @(
    @{ Source='dist/StorageScope.exe'; Target='StorageScope.exe' },
    @{ Source='dist/StorageScope-UpgradeGate.exe'; Target='StorageScope-UpgradeGate.exe' },
    @{ Source="installer/StorageScope-Setup-v$releaseVersion.exe"; Target="StorageScope-Setup-v$releaseVersion.exe" },
    @{ Source="portable/StorageScope-Portable-v$releaseVersion-win-x64.zip"; Target="StorageScope-Portable-v$releaseVersion-win-x64.zip" },
    @{ Source="installer/release-manifest-v$releaseVersion.json"; Target="release-manifest-v$releaseVersion.json" }
  )
  $evidence = @()
  foreach ($entry in $outputs) {
    $origin = Join-Path $PSScriptRoot $entry.Source
    $target = Join-Path $binaryStage $entry.Target
    if (-not (Test-Path -LiteralPath $origin -PathType Leaf)) { throw "Binaire manquant: $origin" }
    Copy-Item -LiteralPath $origin -Destination $target -Force
    $a = (Get-FileHash -LiteralPath $origin -Algorithm SHA256).Hash
    $b = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
    if ($a -ne $b) { throw "Binaire altere pendant copie: $($entry.Target)" }
    $evidence += @{ name=$entry.Target; sha256=$b; bytes=(Get-Item -LiteralPath $target).Length }
  }
  @{ version=$releaseVersion; platform='windows-x64'; generated_utc=(Get-Date).ToUniversalTime().ToString('o'); artifacts=$evidence } |
    ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $binaryStage 'BINARY-MANIFEST.json') -Encoding UTF8
  & python (Join-Path $PSScriptRoot 'verify-binary-delivery.py') --folder $binaryStage --version $releaseVersion
  if ($LASTEXITCODE -ne 0) { throw "Validation binary echouee: $LASTEXITCODE" }
  # Keep previous release in binary/ until new release has been fully verified.
  if (-not (Test-Path -LiteralPath $binaryRoot)) { New-Item -ItemType Directory -Path $binaryRoot -Force | Out-Null }
  $versionDir = Join-Path $binaryRoot ("v" + $releaseVersion)
  if (Test-Path -LiteralPath $versionDir) {
    throw "Version deja presente dans binary: $versionDir (ne pas ecraser un build existant)"
  }
  Move-Item -LiteralPath $binaryStage -Destination $versionDir
  Write-Host "BINAIRES WINDOWS DISPONIBLES: $versionDir"
} catch {
  Write-Error ('Echec publication binary; fichiers conserves: ' + $binaryStage)
  throw
}

if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
