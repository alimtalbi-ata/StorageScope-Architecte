$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'build-all-windows.ps1')
if (-not $?) { throw 'Build failed' }
