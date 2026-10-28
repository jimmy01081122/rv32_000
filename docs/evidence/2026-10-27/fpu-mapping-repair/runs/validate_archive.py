from pathlib import Path
import gzip,hashlib,json
root=Path.cwd();dest=root/'docs/evidence/2026-10-27/fpu-mapping-repair'
sha=lambda b:hashlib.sha256(b).hexdigest()
inventory=json.loads((dest/'copy-inventory.json').read_text());assert inventory['final']
seen=set()
for r in inventory['records']:
 assert r['stored'] not in seen;seen.add(r['stored']);p=dest/r['stored'];raw=p.read_bytes();decoded=gzip.decompress(raw) if r['encoding']=='gzip' else raw
 assert sha(raw)==r['stored_sha256'] and len(raw)==r['stored_bytes'],p
 assert sha(decoded)==r['decoded_sha256'] and len(decoded)==r['decoded_bytes'],p
# Only the gate driver changed after the phase-1 snapshot. Verify every current
# review implementation against its final snapshot, not an earlier failed driver.
source_count=0
for directory in ('experiments/fpu-mapping-v1','physical/asap7/fpu-isolated','physical/asap7/baseline'):
 for p in (root/directory).iterdir():
  if not p.is_file():continue
  prefix='inputs-final' if p.name=='gate_driver.cc' else 'inputs'
  archived=dest/prefix/p.relative_to(root);assert archived.read_bytes()==p.read_bytes(),p;source_count+=1
r=dict(passed=True,copy_records=len(seen),stored_bytes=sum(r['stored_bytes'] for r in inventory['records']),decoded_bytes=sum(r['decoded_bytes'] for r in inventory['records']),current_source_snapshots=source_count)
(dest/'validation.json').write_text(json.dumps(r,indent=2)+'\n')
files=sorted(p for p in dest.rglob('*') if p.is_file() and p.name!='SHA256SUMS')
assert not any(p.is_symlink() for p in files)
(dest/'SHA256SUMS').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(dest)}\n' for p in files))
for line in (dest/'SHA256SUMS').read_text().splitlines():
 h,n=line.split('  ',1);assert sha((dest/n).read_bytes())==h,n
print(json.dumps(dict(**r,indexed_files=len(files))))
