# Windows-only isolated installer smoke test; author Abdelhalim Talbi.
$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -ge 6 -and -not $IsWindows) { throw 'Windows required' }
$root = Split-Path -Parent $PSScriptRoot
$version = (Get-Content (Join-Path $root '07-Manifestes/VERSION') -Raw).Trim()
$installer = Join-Path $PSScriptRoot "installer/StorageScope-Setup-v$version.exe"
if (-not (Test-Path $installer)) { throw "Installer missing: $installer" }
$target = Join-Path $env:TEMP "StorageScope-CI-$([guid]::NewGuid().ToString('N'))"
$report = [ordered]@{version=$version; status='FAIL'; installed=$false; gate_checked=$false; version_checked=$false; uninstalled=$false; error=$null}
$failure = $null
try {
  $p = Start-Process -FilePath $installer -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',"/DIR=$target") -Wait -PassThru
  if ($p.ExitCode -ne 0) { throw "Installer exit $($p.ExitCode)" }
  $report.installed = $true
  $exe = Join-Path $target 'StorageScope.exe'
  if (-not (Test-Path $exe)) { throw 'Installed EXE missing' }
  $gate = Join-Path $target 'StorageScope-UpgradeGate.exe'
  if (-not (Test-Path -LiteralPath $gate -PathType Leaf)) { throw 'Installed upgrade gate missing' }
  if ((Get-Item -LiteralPath $gate).Length -lt 1024) { throw 'Installed upgrade gate unexpectedly small' }
  $report.gate_checked = $true
  $probe = Join-Path $env:TEMP "storagescope-version-$([guid]::NewGuid().ToString('N')).txt"
  try {
    $p = Start-Process -FilePath $exe -ArgumentList @('--version-file',"`"$probe`"") -Wait -PassThru
    if ($p.ExitCode -ne 0 -or -not (Test-Path $probe)) { throw 'Version probe failed' }
    if ((Get-Content -LiteralPath $probe -Raw).Trim() -ne $version) { throw 'Installed version mismatch' }
    $report.version_checked = $true
  } finally { Remove-Item -LiteralPath $probe -Force -ErrorAction SilentlyContinue }
} catch {
  $failure = $_.Exception.Message
} finally {
  try {
    $uninstaller = Join-Path $target 'unins000.exe'
    if (Test-Path $uninstaller) {
      $p = Start-Process -FilePath $uninstaller -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -Wait -PassThru
      $report.uninstalled = ($p.ExitCode -eq 0 -and -not (Test-Path (Join-Path $target 'StorageScope.exe')))
      if (-not $report.uninstalled -and -not $failure) { $failure = "Uninstaller exit $($p.ExitCode) or application remains" }
    } elseif ($report.installed -and -not $failure) { $failure = 'Uninstaller missing' }
  } catch {
    if (-not $failure) { $failure = "Cleanup failed: $($_.Exception.Message)" }
  }
  $report.status = if ($report.installed -and $report.gate_checked -and $report.version_checked -and $report.uninstalled -and -not $failure) { 'PASS' } else { 'FAIL' }
  $report.error = $failure
  $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'windows-installer-smoke-report.json') -Encoding UTF8
}
if ($report.status -ne 'PASS') { throw "Installer smoke failed: $($report.error)" }
