"""Losslessly compact completed B intermediates; retain final routed checkpoint."""
from pathlib import Path
import gzip, hashlib, json, os, shutil

root = Path('/workspace/rv32_000')
out = root / 'build/experiments/lsu-b-diagnosis-v1'
receipt = out / 'idle-cache-compaction.json'
assert not receipt.exists()
def digest(path, compressed=False):
    h = hashlib.sha256()
    with (gzip.open(path, 'rb') if compressed else path.open('rb')) as src:
        for block in iter(lambda: src.read(1024*1024), b''): h.update(block)
    return h.hexdigest()
records=[]
for path in sorted((root/'build/experiments/lsu-b-v1').glob('physical-*/results/**/*.odb')):
    if 'eco-clean-v1' in str(path) and path.name == '5_1_grt.odb': continue
    assert path.stat().st_nlink == 1, path
    target = path.with_suffix(path.suffix+'.gz')
    assert not target.exists(), target
    before=digest(path); size=path.stat().st_size
    with path.open('rb') as src, target.open('xb') as dest:
        with gzip.GzipFile(filename='', mode='wb', fileobj=dest, compresslevel=1, mtime=0) as zipped:
            shutil.copyfileobj(src, zipped, 1024*1024)
    assert digest(target, True) == before
    row=dict(original_path=str(path.relative_to(root)),original_bytes=size,
             original_sha256=before,gzip_path=str(target.relative_to(root)),
             gzip_bytes=target.stat().st_size,gzip_sha256=digest(target),roundtrip_verified=True)
    records.append(row)
    receipt.write_text(json.dumps(dict(scope='idle B intermediates only; no archived bytes changed',records=records),indent=2)+'\n')
    path.unlink()
    print(path.name, size-target.stat().st_size, flush=True)
print('saved_bytes',sum(r['original_bytes']-r['gzip_bytes'] for r in records))
