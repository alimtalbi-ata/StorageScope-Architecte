# Smoke test du binaire Windows; ne lance pas la GUI et ne supprime aucune donnee.
# Auteur: Abdelhalim Talbi
param([string]$Executable = (Join-Path $PSScriptRoot 'dist\StorageScope.exe'), [string]$ExpectedVersion = '5.80')
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) { throw "EXE absent: $Executable" }
$proc = Start-Process -FilePath $Executable -ArgumentList @('--version') -Wait -PassThru -NoNewWindow -RedirectStandardOutput "$env:TEMP\storagescope-version-$PID.txt"
try {
    if ($proc.ExitCode -ne 0) { throw "Echec --version: $($proc.ExitCode)" }
    $version = (Get-Content "$env:TEMP\storagescope-version-$PID.txt" -Raw).Trim()
    if ($version -ne $ExpectedVersion) { throw "Version incorrecte: $version" }
} finally { Remove-Item "$env:TEMP\storagescope-version-$PID.txt" -ErrorAction SilentlyContinue }
$p = Start-Process -FilePath $Executable -ArgumentList @('--self-test') -Wait -PassThru
if ($p.ExitCode -ne 0) { throw "Self-test echoue: $($p.ExitCode)" }
Write-Host "PASS: executable version $ExpectedVersion et self-test"
