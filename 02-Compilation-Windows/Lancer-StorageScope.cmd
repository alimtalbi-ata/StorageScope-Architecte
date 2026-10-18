@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 storagescope_windows.py
) else (
  python storagescope_windows.py
)
if errorlevel 1 (echo. & echo Erreur de lancement. Installez Python 3.11+ avec Tkinter. & pause)
