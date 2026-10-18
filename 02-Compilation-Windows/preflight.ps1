$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$version = (Get-Content (Join-Path $root '07-Manifestes/VERSION') -Raw).Trim()
if ($version -notmatch '^\d+\.\d+$') { throw "Version inattendue: $version" }
foreach ($relative in @('03-Sources/storagescope_windows.py','02-Compilation-Windows/build-engine-windows.ps1','02-Compilation-Windows/StorageScope.spec','02-Compilation-Windows/StorageScope.iss','02-Compilation-Windows/requirements-build.txt')) {
 if (-not (Test-Path -LiteralPath (Join-Path $root $relative) -PathType Leaf)) { throw "Fichier requis absent: $relative" }
}
# Python and Inno Setup are installed by build-engine-windows.ps1 when missing.
# Do not block bootstrap at preflight stage.
if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) { Write-Warning 'Python absent: bootstrap via winget requis dans build-engine-windows.ps1' }
Write-Host "PREFLIGHT PASS - StorageScope $version - aucune compilation executee"
