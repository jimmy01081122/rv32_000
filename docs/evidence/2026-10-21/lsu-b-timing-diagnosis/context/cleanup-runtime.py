"""Release only the completed, idle diagnostic container and replay duplicates."""
from pathlib import Path
import datetime, gzip, hashlib, json, os, shutil, subprocess
root=Path('/workspace/rv32_000');out=root/'build/experiments/lsu-b-diagnosis-v1'
for key in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH'):os.environ.pop(key,None)
docker=['docker','--host=unix:///var/run/docker.sock'];container='rv32-lsu-b-diagnosis-v1'
def load(p):return json.loads(p.read_text())
assert load(out/'native-probes.json')['complete']
assert load(out/'diagnostic-review.json')['passed']
assert load(out/'synthesis-connectivity-review.json')['passed']
record=load(out/'native-probes.json')
actual=json.loads(subprocess.check_output(docker+['inspect',container],text=True))[0]
assert actual['Id']==record['container_id'] and actual['Image']==record['image_id']
top=subprocess.check_output(docker+['top',container,'-eo','pid,args'],text=True)
assert [line.split(maxsplit=1)[1] for line in top.splitlines()[1:]]==['/bin/sleep infinity'],top
command=docker+['exec',container,'sha256sum','--strict','--quiet','-c','/workspace/docs/evidence/2026-10-18/post-lsu-baseline-preparation/environment/physical-tool-platform-sha256.txt']
subprocess.run(command,check=True)
images=subprocess.check_output(docker+['image','ls','--no-trunc','--format','{{.ID}}'],text=True)
before=shutil.disk_usage(root).free
subprocess.run(docker+['rm','-f',container],check=True)
assert subprocess.check_output(docker+['image','ls','--no-trunc','--format','{{.ID}}'],text=True)==images
removed=[]
for row in load(out/'replay-inputs.json')['restorations']:
 p=root/row['restored'];source=root/row['source']
 assert p.parent==out/'replays'
 assert hashlib.sha256(p.read_bytes()).hexdigest()==row['raw_sha256']
 assert hashlib.sha256(source.read_bytes()).hexdigest()==row['source_sha256']
 h=hashlib.sha256()
 with gzip.open(source,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 assert h.hexdigest()==row['raw_sha256']
 removed.append(dict(path=row['restored'],sha256=row['raw_sha256'],restorable_from=row['source']))
 p.unlink()
receipt=dict(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),container_id=actual['Id'],idle_top=top,critical_files_final_verified=204,container_removed=True,pinned_images_unchanged=True,replay_duplicates_removed=removed,original_inputs_and_archives_retained=True,free_bytes_before=before,free_bytes_after=shutil.disk_usage(root).free)
(out/'runtime-cleanup.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('free_GiB',receipt['free_bytes_after']/2**30)
