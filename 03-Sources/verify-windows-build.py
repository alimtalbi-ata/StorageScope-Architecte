"""Static, offline Windows release preflight. Author: Abdelhalim Talbi."""
from pathlib import Path
import re, sys

ROOT = Path(__file__).resolve().parent

def validate():
    source = (ROOT / 'storagescope_windows.py').read_text(encoding='utf-8')
    version = re.search(r"^VERSION = '([^']+)'", source, re.M)
    if not version: raise ValueError('Application version missing')
    version = version.group(1)
    required = ['Construire-StorageScope.cmd', 'StorageScope.spec', 'StorageScope.iss',
                'build-all-windows.ps1', 'requirements-build.txt',
                'qualifier-installation-windows.ps1', 'qualifier-executable-windows.ps1', '.github/workflows/windows-build.yml']
    for name in required:
        if not (ROOT / name).is_file(): raise ValueError(f'Missing build input: {name}')
    iss = (ROOT / 'StorageScope.iss').read_text(encoding='utf-8')
    build = (ROOT / 'build-all-windows.ps1').read_text(encoding='utf-8')
    workflow = (ROOT / '.github/workflows/windows-build.yml').read_text(encoding='utf-8')
    if f'#define AppVersion "{version}"' not in iss: raise ValueError('Inno version mismatch')
    if f"$expectedVersion = '{version}'" not in build: raise ValueError('Build version mismatch')
    for suffix in (f'StorageScope-Setup-v{version}.exe', f'release-manifest-v{version}.json'):
        if suffix not in workflow: raise ValueError(f'CI artifact mismatch: {suffix}')
    if 'PrivilegesRequired=lowest' not in iss or r'DefaultDirName={localappdata}\Programs\StorageScope' not in iss:
        raise ValueError('Unsafe or inconsistent install target')
    spec = (ROOT / 'StorageScope.spec').read_text(encoding='utf-8')
    if 'storagescope_windows.py' not in spec or "name='StorageScope'" not in spec:
        raise ValueError('Invalid executable specification')
    if 'pyinstaller==' not in (ROOT / 'requirements-build.txt').read_text(encoding='utf-8'):
        raise ValueError('Unpinned PyInstaller')
    return version

if __name__ == '__main__':
    try: print('PASS Windows build preflight', validate())
    except Exception as error: print('FAIL Windows build preflight:', error, file=sys.stderr); sys.exit(1)
