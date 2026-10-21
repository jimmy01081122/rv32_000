from pathlib import Path
import gzip,hashlib,json,shutil
ROOT=Path('/workspace/rv32_000');OUT=ROOT/'build/experiments/lsu-b-v1';DST=ROOT/'docs/evidence/2026-10-21/lsu-b'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
inv=json.loads((DST/'copy-inventory.json').read_text());records=[]
for row in inv['records']:
 p=DST/row['archive']
 if p.name.startswith('constraints_') and p.suffix=='.sdc' and p.stat().st_size>1024*1024:
  assert sha(p)==row['archive_sha256']==row['source_sha256'];q=p.with_suffix(p.suffix+'.gz');assert not q.exists()
  with p.open('rb') as f,q.open('wb') as raw:
   with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=6) as z:shutil.copyfileobj(f,z)
  with gzip.open(q,'rb') as f:data=f.read()
  assert hashlib.sha256(data).hexdigest()==row['source_sha256'] and len(data)==row['source_bytes']
  old=row['archive'];row.update(archive=str(q.relative_to(DST)),archive_sha256=sha(q),archive_bytes=q.stat().st_size,gzip_roundtrip_verified=True);p.unlink();records.append({'original_archive':old,'compressed_archive':row['archive'],'original_sha256':row['source_sha256'],'original_bytes':row['source_bytes'],'gzip_bytes':row['archive_bytes'],'roundtrip_verified':True})
assert len(records)==12
receipt=OUT/'archive-constraint-compaction.json';receipt.write_text(json.dumps({'scope':'lossless gzip of large generated SDC copies; original native files and recorded analysis hashes unchanged','records':records,'bytes_saved':sum(r['original_bytes']-r['gzip_bytes'] for r in records)},indent=2)+'\n')
for p in [Path(__file__).resolve(),receipt]:
 q=DST/'context'/p.name;assert not q.exists();shutil.copyfile(p,q);inv['records'].append({'source':str(p.relative_to(ROOT)),'source_sha256':sha(p),'source_bytes':p.stat().st_size,'source_mode':oct(p.stat().st_mode&0o777),'archive':str(q.relative_to(DST)),'archive_sha256':sha(q),'archive_bytes':q.stat().st_size,'gzip_roundtrip_verified':False,'completion_copy':True})
(DST/'copy-inventory.json').write_text(json.dumps(inv,indent=2)+'\n');print('12generated SDCs gzip roundtrip verified; savedbytes',sum(r['original_bytes']-r['gzip_bytes'] for r in records))
