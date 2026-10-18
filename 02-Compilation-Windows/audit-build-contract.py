"""StorageScope Windows build static contract verifier (does not claim Windows qualification)."""
from pathlib import Path
import re,sys,json
root=Path(__file__).resolve().parents[1]
version=(root/'07-Manifestes/VERSION').read_text().strip()
files=['build-all-windows.ps1','build-engine-windows.ps1','preflight.ps1','StorageScope.iss','StorageScope.spec','requirements-build.txt','verify-windows-build.py']
missing=[f for f in files if not (root/'02-Compilation-Windows'/f).is_file()]
allbuild='\n'.join((root/'02-Compilation-Windows'/f).read_text(encoding='utf-8-sig',errors='replace') for f in files if f.endswith(('.ps1','.iss')) and (root/'02-Compilation-Windows'/f).exists())
issues=[]
if missing: issues.append('missing: '+','.join(missing))
if not re.search(r'build-engine-windows\.ps1',allbuild): issues.append('missing engine invocation')
if not re.search(r'PyInstaller',allbuild,re.I): issues.append('missing pyinstaller')
if not re.search(r'ISCC|Inno Setup',allbuild,re.I): issues.append('missing installer invocation')
if not (root/'03-Sources/storagescope_windows.py').exists(): issues.append('missing application entrypoint')
result={'version':version,'platform':'static inspection (Linux-compatible)','status':'FAIL' if issues else 'PASS','issues':issues,'native_windows_build':'NOT_RUN'}
print(json.dumps(result,indent=2));sys.exit(bool(issues))
