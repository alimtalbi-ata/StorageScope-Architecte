import pathlib,sys,json,hashlib
r=pathlib.Path(__file__).resolve().parents[1]
m=json.loads((r/'07-Manifestes/manifest-v623.json').read_text())
errors=[]
for name,sha in m['sha256'].items():
 p=r/name
 if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:errors.append(name)
assert not errors,errors
assert not list(r.rglob('*.pyc'))
assert (r/'07-Manifestes/VERSION').read_text().strip()=='6.23'
print('PASS release integrity:',len(m['sha256']),'files')
