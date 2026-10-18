"""Validate the installer against the generated release manifest (not Authenticode)."""
import argparse, hashlib, json, pathlib, sys
from importlib.machinery import SourceFileLoader

def verify_installer(installer, manifest, version):
    exe=pathlib.Path(installer); mp=pathlib.Path(manifest)
    if not exe.is_file() or not mp.is_file(): raise ValueError('Missing installer or release manifest')
    doc=json.loads(mp.read_text(encoding='utf-8-sig'))
    if doc.get('version')!=version: raise ValueError('Release version mismatch')
    expected=f'StorageScope-Setup-v{version}.exe'
    if exe.name!=expected: raise ValueError('Unexpected installer filename')
    entries=doc.get('artifacts')
    if not isinstance(entries,list): raise ValueError('Invalid artifacts array')
    matching=[x for x in entries if isinstance(x,dict) and x.get('filename')==expected]
    if len(matching)!=1: raise ValueError('Installer must appear exactly once in manifest')
    item=matching[0]; size=exe.stat().st_size
    if size<1024 or size>2*1024**3: raise ValueError('Installer size outside accepted bounds')
    if item.get('bytes')!=size: raise ValueError('Installer size mismatch')
    with exe.open('rb') as f:
        head=f.read(4096)
    if len(head)<64 or head[:2]!=b'MZ': raise ValueError('Installer is not an MZ executable')
    import struct
    offset=struct.unpack_from('<I',head,0x3c)[0]
    if not (64<=offset<=1024 and offset+26<=len(head)): raise ValueError('Invalid PE header offset')
    if head[offset:offset+4]!=b'PE\x00\x00': raise ValueError('Invalid PE signature')
    machine=struct.unpack_from('<H',head,offset+4)[0]
    magic=struct.unpack_from('<H',head,offset+24)[0]
    if (machine, magic) not in ((0x14c,0x10b),(0x8664,0x20b)):
        raise ValueError('Inconsistent PE architecture and optional header')
    sections=struct.unpack_from('<H',head,offset+6)[0]
    optional_size=struct.unpack_from('<H',head,offset+20)[0]
    if not (1<=sections<=96): raise ValueError('Invalid PE section count')
    minimum_optional=96 if magic==0x10b else 112
    if optional_size<minimum_optional or offset+24+optional_size>len(head):
        raise ValueError('Truncated PE optional header')
    section_table=offset+24+optional_size
    if section_table+sections*40>len(head): raise ValueError('Truncated PE section table')
    with exe.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
    if digest.casefold()!=str(item.get('sha256','')).casefold(): raise ValueError('Installer SHA256 mismatch')
    return {'version':version,'installer':expected,'bytes':size,'sha256':digest}

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--installer',required=True); p.add_argument('--manifest',required=True); p.add_argument('--version',required=True); a=p.parse_args()
    try: print('PASS installer release',json.dumps(verify_installer(a.installer,a.manifest,a.version)))
    except Exception as exc: print('FAIL installer release:',exc,file=sys.stderr); sys.exit(1)
