param([string]$BuildDirectory = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$backup = Join-Path $BuildDirectory '.publish-backup'
$pending = Join-Path $BuildDirectory '.publish-pending'
if (-not (Test-Path -LiteralPath $backup)) { Write-Output 'Aucune sauvegarde de publication interrompue.'; exit 0 }
Write-Warning "Sauvegarde detectee: $backup. Ne pas relancer la compilation avant resolution."
foreach ($name in @('dist','installer','portable','build-logs')) {
  $old = Join-Path $backup $name
  $current = Join-Path $BuildDirectory $name
  $staged = Join-Path $pending $name
  Write-Output ([pscustomobject]@{Component=$name; Backup=(Test-Path -LiteralPath $old); Current=(Test-Path -LiteralPath $current); Pending=(Test-Path -LiteralPath $staged)})
}
Write-Output 'Recuperation manuelle : sauvegarder les trois repertoires, comparer leurs manifestes, restaurer les anciens repertoires depuis .publish-backup uniquement apres validation.'
exit 2
