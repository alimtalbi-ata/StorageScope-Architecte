# -*- mode: python ; coding: utf-8 -*-
# Build on Windows: Construire-StorageScope.cmd
from pathlib import Path
from windows_module_inventory import reachable_modules
# Only the static local import closure; do not bundle tests, CLI experiments or benchmarks.
local_modules = reachable_modules(Path('.'))
a = Analysis(['storagescope_windows.py'], pathex=['.'], binaries=[], datas=[], hiddenimports=local_modules, hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='StorageScope', debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False, disable_windowed_traceback=False)
