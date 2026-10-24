# v5.89 - Windows-only fail-closed installer qualification on a disposable runner.
# Author: Abdelhalim Talbi. Never run on a workstation with user data.
param([string]$Version = '5.89')
$ErrorActionPreference = 'Stop'
# Preserve the caller's working directory: the CI checks the JSON report relative to
# the repository root after this script returns. All script resources use $PSScriptRoot.
$setup = Join-Path $PSScriptRoot ("installer\StorageScope-Setup-v{0}.exe" -f $Version)
$install = Join-Path $env:LOCALAPPDATA 'Programs\StorageScope'
$data = Join-Path $env:LOCALAPPDATA 'StorageScope'
$logDir = Join-Path $PSScriptRoot 'build-logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("installer-rejected-v{0}.log" -f $Version)
$report = Join-Path $logDir ("installer-rejected-v{0}.json" -f $Version)
if (-not (Test-Path -LiteralPath $setup -PathType Leaf)) { throw "Installateur absent: $setup" }
if ((Test-Path -LiteralPath $install) -or (Test-Path -LiteralPath $data)) {
    throw 'REFUS: VM non vierge; ne jamais ecraser des donnees utilisateur.'
}
$fixture = Join-Path $data 'architecture-decisions.sqlite'
$created = $false
try {
    New-Item -ItemType Directory -Path $data -Force | Out-Null
    $created = $true
    # A corrupt database must be rejected before installation or overwrite.
    [IO.File]::WriteAllBytes($fixture, [Text.Encoding]::ASCII.GetBytes('NOT-A-SQLITE-DATABASE'))
    $before = (Get-FileHash -LiteralPath $fixture -Algorithm SHA256).Hash
    $args = @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',("/LOG=`"{0}`"" -f $log))
    $p = Start-Process -FilePath $setup -ArgumentList $args -Wait -PassThru
    $after = (Get-FileHash -LiteralPath $fixture -Algorithm SHA256).Hash
    $logPresent = Test-Path -LiteralPath $log -PathType Leaf
    $logBytes = if ($logPresent) { (Get-Item -LiteralPath $log).Length } else { 0 }
    $binaryPresent = Test-Path -LiteralPath (Join-Path $install 'StorageScope.exe')
    $result = [ordered]@{
        version=$Version; scenario='corrupt-sqlite-installer-rejection'
        exit_code=$p.ExitCode; source_unchanged=($before -eq $after)
        installed_binary_present=$binaryPresent; log_present=$logPresent
        log_bytes=$logBytes; passed=($p.ExitCode -ne 0 -and $before -eq $after -and -not $binaryPresent -and $logBytes -gt 0)
    }
    $result | ConvertTo-Json | Set-Content -LiteralPath $report -Encoding UTF8
    if (-not $result.passed) { throw "FAIL: installer gate scenario; report=$report" }
    Write-Host "PASS: installer refuses corrupt database without changing user data. Log=$log"
} finally {
    # Remove only our exact fixture and the empty directory we created.
    # Never remove an unexpected file or installation, even on failure.
    if ($created -and (Test-Path -LiteralPath $fixture -PathType Leaf)) {
        $expected = [Text.Encoding]::ASCII.GetBytes('NOT-A-SQLITE-DATABASE')
        $actual = [IO.File]::ReadAllBytes($fixture)
        if ([Convert]::ToBase64String($expected) -eq [Convert]::ToBase64String($actual)) {
            Remove-Item -LiteralPath $fixture -Force
        } else { Write-Warning 'Fixture modified: left in place for investigation.' }
    }
    if ($created -and (Test-Path -LiteralPath $data)) {
        if (@(Get-ChildItem -LiteralPath $data -Force).Count -eq 0) { Remove-Item -LiteralPath $data }
        else { Write-Warning 'Data directory not empty: left intact.' }
    }
}
