# Native Windows portable smoke test; auteur Abdelhalim Talbi.
$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -ge 6 -and -not $IsWindows) { throw 'Windows required' }
$root = Split-Path -Parent $PSScriptRoot
$version = (Get-Content (Join-Path $root '07-Manifestes/VERSION') -Raw).Trim()
$archive = Join-Path $PSScriptRoot "portable/StorageScope-Portable-v$version-win-x64.zip"
$reportPath = Join-Path $PSScriptRoot 'windows-portable-smoke-report.json'
$report = [ordered]@{ version=$version; status='FAIL'; archive_present=$false; extracted=$false; version_checked=$false; self_test=$false; cleanup=$false; error=$null }
$tempDir = Join-Path $env:TEMP ("StorageScope-Portable-CI-" + [guid]::NewGuid().ToString('N'))
$failure = $null
try {
  if (-not (Test-Path -LiteralPath $archive -PathType Leaf)) { throw "Portable missing: $archive" }
  $report.archive_present = $true
  New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
  Expand-Archive -LiteralPath $archive -DestinationPath $tempDir -Force
  $report.extracted = $true
  $exeList = @(Get-ChildItem -LiteralPath $tempDir -Filter 'StorageScope.exe' -File -Recurse)
  if ($exeList.Count -ne 1) { throw "Expected one portable executable, got $($exeList.Count)" }
  $exe = $exeList[0].FullName
  $probe = Join-Path $tempDir 'version-probe.txt'
  $p = Start-Process -FilePath $exe -ArgumentList @('--version-file', ('"' + $probe + '"')) -Wait -PassThru
  if ($p.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $probe)) { throw 'Portable version probe failed' }
  if ((Get-Content -LiteralPath $probe -Raw).Trim() -ne $version) { throw 'Portable version mismatch' }
  $report.version_checked = $true
  $p = Start-Process -FilePath $exe -ArgumentList @('--self-test') -Wait -PassThru
  if ($p.ExitCode -ne 0) { throw "Portable self-test failed: $($p.ExitCode)" }
  $report.self_test = $true
} catch {
  $failure = $_.Exception.Message
} finally {
  try {
    if (Test-Path -LiteralPath $tempDir) { Remove-Item -LiteralPath $tempDir -Recurse -Force }
    $report.cleanup = -not (Test-Path -LiteralPath $tempDir)
  } catch { if (-not $failure) { $failure = "Cleanup failed: $($_.Exception.Message)" } }
  $report.status = if ($report.archive_present -and $report.extracted -and $report.version_checked -and $report.self_test -and $report.cleanup -and -not $failure) { 'PASS' } else { 'FAIL' }
  $report.error = $failure
  $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding UTF8
}
if ($report.status -ne 'PASS') { throw "Portable smoke failed: $($report.error)" }
