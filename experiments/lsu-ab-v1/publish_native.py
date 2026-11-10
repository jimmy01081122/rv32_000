#!/usr/bin/env python3
"""Verify completed native evidence is already durable in both namespaces."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from publish_stream import stream_copy

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').is_file())
BASE = ROOT/'build/experiments/lsu-ab-v1/native'
MOUNT = '/workspace/build/experiments/lsu-ab-v1/native'
GUEST = MOUNT
CONTAINER = 'rv32-ab-native'
DOCKER = ['env', '-u', 'DOCKER_HOST', '-u', 'DOCKER_CONTEXT', '-u', 'DOCKER_TLS',
          '-u', 'DOCKER_TLS_VERIFY', '-u', 'DOCKER_CERT_PATH', 'docker',
          '--host=unix:///var/run/docker.sock']

INVENTORY = r'''
import hashlib,json,os,stat,sys
from pathlib import Path
b=Path(sys.argv[1]);rows=[]
for p in sorted(b.rglob('*')):
    r={'path':str(p.relative_to(b))};mode=p.lstat().st_mode
    if stat.S_ISLNK(mode):
        target=os.readlink(p)
        if Path(target).is_absolute() or not p.resolve(strict=True).is_relative_to(b):
            raise ValueError('nonlocal or dangling evidence link: '+str(p))
        r.update(kind='symlink',target=target)
    elif stat.S_ISDIR(mode):r.update(kind='directory')
    elif stat.S_ISREG(mode):
        h=hashlib.sha256()
        with p.open('rb') as f:
            for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
        r.update(kind='file',bytes=p.stat().st_size,sha256=h.hexdigest(),inode=p.stat().st_ino,device=p.stat().st_dev)
    else:raise ValueError('unexpected evidence file type: '+str(p))
    rows.append(r)
print(json.dumps(rows))
'''


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def native_json(name):
    return json.loads(subprocess.check_output(DOCKER+['exec', CONTAINER, 'cat', GUEST+'/'+name], text=True))


def inventory():
    return json.loads(subprocess.check_output(DOCKER+['exec', CONTAINER, 'python3', '-c', INVENTORY, GUEST], text=True))


def verify(root, rows, allow_missing=False):
    for row in rows:
        relative = Path(row['path'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'unsafe inventory path')
        p = root/relative
        # Ancestors must be real directories; never copy through an existing host link.
        for parent in p.parents:
            if parent == root:
                break
            require(not parent.is_symlink(), 'host ancestor is a symlink: '+str(parent))
        if allow_missing and not p.exists() and not p.is_symlink():
            continue
        if row['kind'] == 'symlink':
            require(p.is_symlink() and os.readlink(p) == row['target'], 'link differs: '+str(p))
            require(p.resolve(strict=True).is_relative_to(root), 'link leaves publication root')
        elif row['kind'] == 'directory':
            require(p.is_dir() and not p.is_symlink(), 'directory differs: '+str(p))
        else:
            require(p.is_file() and not p.is_symlink() and p.stat().st_size == row['bytes']
                    and sha(p) == row['sha256'], 'file differs: '+str(p))


def main():
    output = BASE/'native-publication.json'
    require(not output.exists(), 'preserve earlier publication receipt')
    state = dict(scope='verify direct durable host evidence; no physical qualification',
                 started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 publisher_sha256=sha(Path(__file__)), stream_copy_sha256=sha(Path(__file__).with_name('publish_stream.py')), container=CONTAINER, passed=False)
    def save():
        output.write_text(json.dumps(state, indent=2)+'\n')
    try:
        status = native_json('native-exit.json')
        controller = native_json('physical-controller.json')
        require(status['returncode'] == 0 and controller['complete']
                and controller['stages'] == ['grt', 'eco', 'guard'], 'native construction incomplete')
        for directory, stages in [('physical-AB-v1', ['grt']), ('physical-AB-v2', ['grt-reused', 'eco']),
                                  ('physical-AB-v4', ['guard'])]:
            pipeline = native_json(directory+'/pipeline.json')
            require(pipeline['complete'] and pipeline['variant'] == 'AB'
                    and pipeline['stages'] == stages, 'incomplete pipeline: '+directory)
        storage = ROOT/'build/experiments/lsu-ab-v1/checkpoints/native-storage.json'
        proof = json.loads(storage.read_text())
        require(proof['passed'] and proof['mode'] == 'direct_host_bind'
                and proof['private_tmpfs_unmounted'], 'direct host storage required')
        require(sha(BASE/'host-storage-marker.json') == proof['marker_sha256'], 'storage marker changed')
        require(controller['storage_receipt_sha256'] == sha(storage), 'controller storage receipt changed')
        mounts = subprocess.check_output(DOCKER+['exec', CONTAINER, 'cat', '/proc/self/mountinfo'], text=True)
        require(not any(' '+MOUNT+' ' in line for line in mounts.splitlines()), 'private output mount must be absent')
        state.update(publication_mode='direct_host_bind', storage_receipt_sha256=sha(storage),
                     private_tmpfs_unmounted=True)
        # Only completed immutable OpenDB/SDC copies are deduplicated. All bytes
        # remain available at their original paths; The namespace tar stream preserves hardlinks.
        dedup_code = r"""
+import hashlib,json,os,sys
+from pathlib import Path
+b=Path(sys.argv[1]);seen={};rows=[]
+for p in sorted(b.rglob('*')):
+ if p.is_symlink() or not p.is_file() or p.suffix not in ('.odb','.sdc'):continue
+ h=hashlib.sha256()
+ with p.open('rb') as f:
+  for data in iter(lambda:f.read(1048576),b''):h.update(data)
+ key=(p.stat().st_size,h.hexdigest())
+ if key not in seen:seen[key]=p;continue
+ prior=seen[key]
+ if p.stat().st_ino==prior.stat().st_ino:continue
+ temporary=p.with_name(p.name+'.hardlink-tmp');os.link(prior,temporary);os.replace(temporary,p)
+ rows.append(dict(path=str(p.relative_to(b)),same_as=str(prior.relative_to(b)),sha256=key[1],bytes=key[0]))
+print(json.dumps(rows))
+""".replace('\n+', '\n')
        dedup = json.loads(subprocess.check_output(DOCKER+['exec', CONTAINER, 'python3', '-c', dedup_code, GUEST], text=True))
        state['completed_database_hardlinks'] = dedup
        rows = inventory()
        require(rows, 'empty native inventory')
        verify(BASE, rows)
        unique_files = {(r['device'],r['inode']):r['bytes'] for r in rows if r['kind']=='file'}
        require(inventory() == rows, 'native evidence changed while verifying')
        state.update(controller=controller, native_exit=status, files=rows,
                     file_bytes=sum(unique_files.values()), host_free_before_bytes=shutil.disk_usage(BASE).free,
                     all_host_bytes_and_links_verified=True, phase='verify-shared-view')
        save()
        # The native and host namespaces must now see the exact published files.
        # Verify in a plain Python process inside the container, without recursively invoking Docker.
        verifier = "import json,hashlib,os,sys;from pathlib import Path\nb=Path(sys.argv[1]);d=json.loads((b/'native-publication.json').read_text())\nfor r in d['files']:\n p=b/r['path']\n if r['kind']=='file':\n  h=hashlib.sha256()\n  with p.open('rb') as f:\n   for x in iter(lambda:f.read(1048576),b''):h.update(x)\n  assert p.stat().st_size==r['bytes'] and h.hexdigest()==r['sha256'],str(p)\n elif r['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==r['target'],str(p)\n else:assert p.is_dir() and not p.is_symlink(),str(p)\nprint('published native view verified')"
        subprocess.run(DOCKER+['exec', CONTAINER, 'python3', '-c', verifier, GUEST], check=True)
        platform = '/workspace/docs/evidence/2026-10-18/post-lsu-baseline-preparation/environment/physical-tool-platform-sha256.txt'
        subprocess.run(DOCKER+['exec', CONTAINER, 'sha256sum', '--strict', '--quiet', '-c', platform], check=True)
        state.update(passed=True, phase='complete', critical_platform_files_verified=204,
                     finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        save()
        print(json.dumps({k: v for k, v in state.items() if k not in ('files', 'controller')}, indent=2))
    except Exception as error:
        state['error'] = str(error)
        save()
        raise


if __name__ == '__main__':
    main()
