# Windows build dependencies — GitHub runner

Build host: GitHub Actions `windows-latest` with Python 3.12.
Declared Python build dependency: `pyinstaller==6.16.0`.
Installer tool: Inno Setup 6 (`ISCC.exe`), discovered or bootstrapped by the existing build scripts.
No Python installation should be required on the end-user Windows workstation.

## Outputs expected
- `binary/v<version>/StorageScope.exe`
- `binary/v<version>/StorageScope-Setup-v<version>.exe`
- `binary/v<version>/StorageScope-Portable-v<version>-win-x64.zip`

The GitHub workflow fails closed if expected files or the existing delivery verification are missing.
An Actions artifact is published only on success.

**Qualification caveat:** the GitHub main branch is v6.108; the v6.113 cumulative
sources are not yet merged. Builds of this branch are therefore not the full v6.114
product. No Windows executable is certified until CI reports a successful run.
Auteur : Abdelhalim Talbi.
