"""Verify Windows portable archive after build; no third-party dependencies.
Author: Abdelhalim Talbi.
"""
import argparse, hashlib, json, pathlib, struct, sys, zipfile

def validate_pe_amd64(stream):
    """Check Windows PE32+ AMD64 header, not a code-signature verification."""
    header = stream.read(4096)
    if len(header) < 0x40 or header[:2] != b'MZ':
        raise ValueError('Not a Windows PE executable (MZ)')
    pe_offset = struct.unpack_from('<I', header, 0x3c)[0]
    if pe_offset < 0x40 or pe_offset > 1024 or pe_offset + 26 > len(header):
        raise ValueError('Invalid PE header offset')
    if header[pe_offset:pe_offset+4] != b'PE\x00\x00':
        raise ValueError('Invalid PE signature')
    machine = struct.unpack_from('<H', header, pe_offset+4)[0]
    optional_size = struct.unpack_from('<H', header, pe_offset+20)[0]
    optional_magic = struct.unpack_from('<H', header, pe_offset+24)[0]
    if machine != 0x8664 or optional_magic != 0x20b or optional_size < 0x70:
        raise ValueError('Expected PE32+ AMD64 executable')

def verify(zip_path, manifest_path, version):
    archive=pathlib.Path(zip_path); manifest=json.loads(pathlib.Path(manifest_path).read_text(encoding='utf-8-sig'))
    if manifest.get('version') != version: raise ValueError('Version mismatch')
    expected={'StorageScope.exe','LIRE-AVANT-UTILISATION.txt',f'portable-manifest-v{version}.json'}
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        if set(names)!=expected or len(names)!=len(expected): raise ValueError('Unexpected/missing/duplicate ZIP members')
        if z.testzip() is not None: raise ValueError('Corrupt portable ZIP')
        info=z.getinfo('StorageScope.exe')
        if info.file_size < 1024: raise ValueError('Executable too small')
        if info.file_size > 1024*1024*1024: raise ValueError('Executable exceeds 1 GiB safety bound')
        if info.compress_size == 0: raise ValueError('Empty compressed executable')
        digest=hashlib.sha256()
        with z.open('StorageScope.exe') as f:
            validate_pe_amd64(f)
        with z.open('StorageScope.exe') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''): digest.update(chunk)
        if digest.hexdigest().upper()!=str(manifest.get('sha256','')).upper(): raise ValueError('EXE SHA256 mismatch')
        if info.file_size != manifest.get('bytes'): raise ValueError('EXE size mismatch')
        embedded=json.loads(z.read(f'portable-manifest-v{version}.json').decode('utf-8-sig'))
        if embedded != manifest: raise ValueError('Embedded manifest differs')
    return {'version':version,'zip_bytes':archive.stat().st_size,'exe_bytes':info.file_size,'exe_sha256':digest.hexdigest()}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--zip',required=True);p.add_argument('--manifest',required=True);p.add_argument('--version',required=True)
    a=p.parse_args()
    try:print('PASS portable release',json.dumps(verify(a.zip,a.manifest,a.version)))
    except Exception as e:print('FAIL portable release',e,file=sys.stderr);sys.exit(1)
