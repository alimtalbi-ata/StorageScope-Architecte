param([string]$InstallPath = '', [switch]$SkipInstaller)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$version = (Get-Content (Join-Path $root '07-Manifestes/VERSION') -Raw).Trim()
$report = [ordered]@{version=$version; timestamp_utc=(Get-Date).ToUniversalTime().ToString('o'); host=$env:COMPUTERNAME; checks=@(); overall='FAIL'}
function Check([string]$name,[scriptblock]$action) {
  try { & $action; $script:report.checks += @{name=$name; status='PASS'} }
  catch { $script:report.checks += @{name=$name; status='FAIL'; error="$($_.Exception.Message)"} }
}
Check 'release_version' { if ($version -notmatch '^\d+\.\d+$') { throw 'Invalid version' } }
Check 'build_launcher' { if (-not (Test-Path (Join-Path $root 'Construire-StorageScope.cmd'))) { throw 'Missing launcher' } }
if (-not $IsWindows -and $PSVersionTable.PSVersion.Major -ge 6) { throw 'Native qualification requires Windows' }
$dist = Join-Path $PSScriptRoot 'dist/StorageScope.exe'
$setup = Join-Path $PSScriptRoot "installer/StorageScope-Setup-v$version.exe"
if (-not $SkipInstaller) { Check 'release_manifest' { $m = Join-Path $PSScriptRoot ("installer/release-manifest-v$version.json"); if (-not (Test-Path $m)) { throw 'Release manifest missing' }; $manifest = Get-Content -LiteralPath $m -Raw | ConvertFrom-Json; if ($manifest.version -ne $version) { throw 'Release manifest version mismatch' }; foreach ($a in $manifest.artifacts) { $candidates = @((Join-Path $PSScriptRoot ('dist/' + $a.filename)), (Join-Path $PSScriptRoot ('installer/' + $a.filename))); $found = @($candidates | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object { Get-Item -LiteralPath $_ }); if ($found.Count -ne 1) { throw "Artifact missing/ambiguous: $($a.filename)" }; if ((Get-FileHash -LiteralPath $found[0].FullName -Algorithm SHA256).Hash -ne $a.sha256) { throw "Artifact hash mismatch: $($a.filename)" } } } }
Check 'compiled_executable' { if (-not (Test-Path $dist)) { throw 'EXE not built' }; if ((Get-Item $dist).Length -lt 1024) { throw 'EXE too small' } }
if (Test-Path $dist) {
  Check 'executable_version' { $probe = Join-Path $PSScriptRoot 'version-probe-build.txt'; if (Test-Path $probe) { Remove-Item $probe -Force }; & $dist --version-file $probe; if ($LASTEXITCODE -ne 0 -or -not (Test-Path $probe)) { throw 'Version probe failed' }; $out = (Get-Content $probe -Raw).Trim(); Remove-Item $probe -Force; if ($out -ne $version) { throw "Expected $version got $out" } }
  Check 'executable_self_test' { & $dist --self-test; if ($LASTEXITCODE -ne 0) { throw "Self-test failed: $LASTEXITCODE" } }
}
if (-not $SkipInstaller) { Check 'installer_present' { if (-not (Test-Path $setup)) { throw 'Installer missing' }; if ((Get-Item $setup).Length -lt 1024) { throw 'Installer too small' } } }
if ($InstallPath) { Check 'installed_executable' { $exe=Join-Path $InstallPath 'StorageScope.exe'; if (-not (Test-Path $exe)) { throw 'Installed executable missing' }; $probe = Join-Path $PSScriptRoot 'version-probe-installed.txt'; if (Test-Path $probe) { Remove-Item $probe -Force }; & $exe --version-file $probe; if ($LASTEXITCODE -ne 0 -or -not (Test-Path $probe)) { throw 'Installed version probe failed' }; $installedVersion = (Get-Content $probe -Raw).Trim(); Remove-Item $probe -Force; if ($installedVersion -ne $version) { throw "Installed version mismatch: $installedVersion" } } }
if (@($report.checks | Where-Object status -eq 'FAIL').Count -eq 0) { $report.overall='PASS' }
$out = Join-Path $PSScriptRoot 'windows-qualification-report.json'
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $out -Encoding UTF8
Write-Host "Qualification: $($report.overall) - $out"
if ($report.overall -ne 'PASS') { exit 1 }
