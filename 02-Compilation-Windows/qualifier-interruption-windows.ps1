# Windows-only, non-destructive interruption rehearsal; does NOT execute installer.
# Author: Abdelhalim Talbi
param([Parameter(Mandatory=$true)][string]$DataDir,
      [Parameter(Mandatory=$true)][string]$BackupDir)
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot '.build-venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'Build venv absent: run Construire-StorageScope.cmd first' }
$script = @'
import json,sys
from upgrade_interruption_v584 import rehearse
print(json.dumps(rehearse(sys.argv[1],sys.argv[2]),ensure_ascii=False))
'@
& $python -c $script $DataDir $BackupDir
if ($LASTEXITCODE -ne 0) { throw 'Interruption rehearsal failed' }
