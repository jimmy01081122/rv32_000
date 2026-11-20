"""Temporarily park verified inactive images and losslessly compact historical A caches."""
import gzip,hashlib,json,os,shutil,subprocess
from pathlib import Path
BASE=Path('build/experiments/lsu-rob-room-v1');OLD=Path('build/experiments/lsu-ab-v1')
D=['env','-u','DOCKER_HOST','-u','DOCKER_CONTEXT','-u','DOCKER_TLS','-u','DOCKER_TLS_VERIFY','-u','DOCKER_CERT_PATH','docker','--host=unix:///var/run/docker.sock']
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(1048576),b''):h.update(x)
 return h.hexdigest()
receipt=BASE/'temporary-capacity.json';assert not receipt.exists()
cache=OLD/'image-cache-v2';saved=json.loads((cache/'summary.json').read_text());archive=cache/'rv32-inactive-images.tar.gz'
assert saved['complete'] and archive.stat().st_size==saved['archive_bytes'] and sha(archive)==saved['archive_sha256']
for tag,digest in saved['images'].items():
 assert subprocess.check_output(D+['image','inspect',tag,'--format','{{.Id}}'],text=True).strip()==digest
 assert not subprocess.check_output(D+['ps','-a','-q','--filter','ancestor='+digest],text=True).strip()
old=json.loads((OLD/'historical-native-compaction.json').read_text());records=old['records']
for row in records:
 path=Path(row['path']);z=Path(row['gzip']);assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256'] and sha(z)==row['gzip_sha256']
 h=hashlib.sha256();n=0
 with gzip.open(z,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b);n+=len(b)
 assert n==row['bytes'] and h.hexdigest()==row['sha256']
state=dict(passed=False,restore_pending=True,scope=__doc__,before_free_bytes=shutil.disk_usage(BASE).free,image_backup=str(archive),image_backup_sha256=sha(archive),images=saved['images'],historical_files=records,script_sha256=sha(Path(__file__)))
def save():receipt.write_text(json.dumps(state,indent=2)+'\n')
save()
# Every deleted raw cache has just been fully decoded and hash checked above.
for row in records:Path(row['path']).unlink()
command=D+['image','rm',*saved['images']]
with (BASE/'temporary-image-removal.log').open('x') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
state.update(command=command,returncode=r.returncode,log_sha256=sha(BASE/'temporary-image-removal.log'),after_free_bytes=shutil.disk_usage(BASE).free,passed=r.returncode==0);save()
assert r.returncode==0
print(json.dumps({k:v for k,v in state.items() if k not in ('historical_files','command')},indent=2))
