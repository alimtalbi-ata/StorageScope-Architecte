"""Validate a Windows delivery before promotion; no binary compilation is performed."""
import argparse,hashlib,json,pathlib,sys

def validate(folder, version):
    folder=pathlib.Path(folder)
    expected={"StorageScope.exe", "StorageScope-UpgradeGate.exe",f"StorageScope-Setup-v{version}.exe",f"StorageScope-Portable-v{version}-win-x64.zip",f"release-manifest-v{version}.json"}
    manifest=folder/'BINARY-MANIFEST.json'
    if not manifest.is_file() or manifest.is_symlink():raise ValueError('Missing/linked manifest')
    data=json.loads(manifest.read_text(encoding='utf-8-sig'))
    if data.get('version')!=version or data.get('platform')!='windows-x64':raise ValueError('Incorrect version/platform')
    artifacts=data.get('artifacts')
    if not isinstance(artifacts,list) or len(artifacts)!=len(expected):raise ValueError('Incorrect artifact count')
    names=[item.get('name') for item in artifacts]
    if len(set(names))!=len(names) or set(names)!=expected:raise ValueError('Missing, unexpected or duplicate artifact')
    for item in artifacts:
        path=folder/item['name']
        if not path.is_file() or path.is_symlink():raise ValueError('Missing or linked artifact: '+item['name'])
        size=path.stat().st_size
        if size<=0 or size!=item.get('bytes'):raise ValueError('Incorrect file size: '+item['name'])
        with path.open('rb') as handle: digest=hashlib.file_digest(handle,'sha256').hexdigest().upper()
        if digest!=str(item.get('sha256','')).upper():raise ValueError('SHA256 mismatch: '+item['name'])
    if {p.name for p in folder.iterdir()}!=expected|{'BINARY-MANIFEST.json'}:raise ValueError('Unexpected files in delivery')
    return len(artifacts)

def main():
    p=argparse.ArgumentParser();p.add_argument('--folder',required=True);p.add_argument('--version',required=True)
    args=p.parse_args()
    try: print('Validated',validate(args.folder,args.version),'artifacts');return 0
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:print('INVALID:',exc,file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
