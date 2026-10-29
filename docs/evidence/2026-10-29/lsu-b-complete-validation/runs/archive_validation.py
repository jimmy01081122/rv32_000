"""Archive selected completed B evidence losslessly; never modify source artifacts."""
from pathlib import Path
import argparse,datetime,gzip,hashlib,json,shutil,subprocess
ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--selection',type=Path,required=True);args=ap.parse_args();root=Path.cwd();out=args.output.resolve();assert out.is_relative_to(root/'docs/evidence') and not out.exists();selection=json.loads(args.selection.read_text());out.mkdir(parents=True);rows=[];excluded=[];sha=lambda data:hashlib.sha256(data).hexdigest()
for choice in selection['entries']:
 source=root/choice['source'];destination=out/choice['destination'];assert source.exists();files=sorted(source.rglob('*')) if source.is_dir() else [source]
 for path in files:
  if not path.is_file():continue
  relative=path.relative_to(source) if source.is_dir() else Path(path.name)
  if path.is_symlink() or '__pycache__' in path.parts or path.suffix=='.pyc':
   excluded.append(dict(source=str(path.relative_to(root)),reason='reproducible convenience alias or Python bytecode'));continue
  # Keep all final/incoming GRT checkpoints, omit reproducible intermediate ODB caches.
  if choice.get('omit_intermediate_odb') and (path.name.endswith('.odb') or path.name.endswith('.odb.gz')) and path.name not in ['5_1_grt.odb','5_1_grt.odb.gz','5_0_grt_input.odb','5_0_grt_input.odb.gz']:
   excluded.append(dict(source=str(path.relative_to(root)),reason='intermediate ODB cache; native stage logs/hashes retained; rebuild from pinned flow'));continue
  target=destination/relative if source.is_dir() else destination
  assert target.is_relative_to(out);target.parent.mkdir(parents=True,exist_ok=True);raw=path.read_bytes();encoding='copy'
  if len(raw)>256*1024 and path.suffix not in ['.gz','.png','.jpg']:
   target=Path(str(target)+'.gz');encoding='gzip';assert not target.exists()
   with gzip.GzipFile(filename=str(target),mode='wb',mtime=0) as stream:stream.write(raw)
   assert gzip.decompress(target.read_bytes())==raw
  else:
   assert not target.exists();target.write_bytes(raw);assert target.read_bytes()==raw
  rows.append(dict(source=str(path.relative_to(root)),destination=str(target.relative_to(out)),encoding=encoding,source_sha256=sha(raw),stored_sha256=sha(target.read_bytes()),source_bytes=len(raw),stored_bytes=target.stat().st_size))
(out/'copy-inventory.json').write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),scope='exact selected completed native evidence and source snapshots; lossless compression only',records=rows,excluded=excluded),indent=2)+'\n')
(out/'archive-selection.json').write_bytes(args.selection.read_bytes())
print(json.dumps(dict(copied_files=len(rows),source_bytes=sum(r['source_bytes'] for r in rows),stored_bytes=sum(r['stored_bytes'] for r in rows),excluded=len(excluded))))
