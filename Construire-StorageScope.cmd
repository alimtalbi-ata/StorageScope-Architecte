@echo off
setlocal EnableExtensions
cd /d "%~dp0"
where powershell.exe >nul 2>&1 || (echo [ERREUR] Windows PowerShell est requis. & exit /b 1)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp002-Compilation-Windows\build-all-windows.ps1"
if errorlevel 1 (
  echo [ECHEC] Voir les messages ci-dessus.
  exit /b 1
)
for /f "usebackq delims=" %%V in ("%~dp007-Manifestes\VERSION") do set "SS_VERSION=%%V"
echo [OK] Binaires publies dans binary\v%SS_VERSION%\
exit /b 0
