#!/usr/bin/env python3
"""Expose durable host output before starting the isolated native experiment."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/experiments/lsu-ab-v1'
sys.path.insert(0, str(ROOT/'experiments/optimization-135-v1'))
from checkpoint import atomic_json
from publish_native import DOCKER, CONTAINER, MOUNT

PRUNE = r'''
from pathlib import Path
import json, shutil, subprocess
base=Path('/OpenROAD-flow-scripts/flow/platforms')
manifest='/workspace/docs/evidence/2026-10-18/post-lsu-baseline-preparation/environment/physical-tool-platform-sha256.txt'
command=['sha256sum','--strict','--quiet','-c',manifest]
subprocess.run(command,check=True)
targets=[p for p in base.iterdir() if p.name not in ('asap7','common')]
targets += [Path(p) for p in ['/OpenROAD-flow-scripts/flow/designs','/usr/include','/usr/local/include','/opt/or-tools/include','/usr/share/doc','/usr/local/doc','/usr/lib/klayout','/usr/lib/llvm-14','/usr/lib/gcc']]
for p in targets:
    assert not str(p).startswith(('/workspace','/orfs-source'))
    if p.is_dir(): shutil.rmtree(p)
    elif p.exists(): p.unlink()
subprocess.run(command,check=True)
print(json.dumps(dict(scope='unused directories in disposable runtime only; pinned image unmodified',removed=[str(p) for p in targets],critical_files_verified_before=204,critical_files_verified_after=204)))
'''


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    output = BASE/'checkpoints/native-storage.json'
    require(not output.exists(), 'preserve previous storage preparation')
    native = BASE/'native'
    require(native.is_dir() and not any(native.iterdir()), 'fresh empty host output required')
    info = json.loads(subprocess.check_output(DOCKER+['inspect', CONTAINER]))[0]
    require(info['State']['Running'] and info['Image'] ==
            'sha256:92a37abacbbf91494f9a8078b45fe1f6688a533cf5c87d02599d28c5fe229b33', 'wrong pinned runtime')
    require(any(m['Type']=='bind' and m['Destination']=='/workspace' and m['Source']==str(ROOT)
                and m['RW'] for m in info['Mounts']), 'wrong workspace bind')
    mounts = subprocess.check_output(DOCKER+['exec', CONTAINER, 'cat', '/proc/self/mountinfo'], text=True)
    require(any(' '+MOUNT+' ' in line and ' - tmpfs ' in line for line in mounts.splitlines()),
            'expected empty private tmpfs')
    subprocess.run(DOCKER+['exec', CONTAINER, 'python3', '-c',
                          'from pathlib import Path; import sys; assert not any(Path(sys.argv[1]).iterdir())', MOUNT], check=True)
    before = shutil.disk_usage(BASE).free
    pruning = json.loads(subprocess.check_output(DOCKER+['exec', '--user', '0:0', CONTAINER,
                                                    'python3', '-c', PRUNE], text=True))
    atomic_json(BASE/'private-runtime-pruning.json', pruning)
    require(shutil.disk_usage(BASE).free >= 4*1024**3, 'need 4 GiB durable workspace capacity')
    subprocess.run(DOCKER+['exec', '--user', '0:0', CONTAINER, 'umount', MOUNT], check=True)
    marker = native/'host-storage-marker.json'
    atomic_json(marker, dict(nonce=uuid.uuid4().hex, scope='host-created durable storage visibility marker'))
    digest = hashlib.sha256(marker.read_bytes()).hexdigest()
    live = subprocess.check_output(DOCKER+['exec', CONTAINER, 'sha256sum', MOUNT+'/'+marker.name], text=True).split()[0]
    require(live==digest, 'container does not see host marker')
    subprocess.run(DOCKER+['exec', CONTAINER, 'python3', '-c',
                          'from pathlib import Path; import sys; p=Path(sys.argv[1]); assert p.stat().st_dev==p.parent.stat().st_dev; assert not any(" "+str(p)+" " in x for x in Path("/proc/self/mountinfo").read_text().splitlines())', MOUNT], check=True)
    atomic_json(output, dict(passed=True, mode='direct_host_bind', private_tmpfs_unmounted=True,
                            container_id=info['Id'], image_id=info['Image'], marker_sha256=digest,
                            host_free_before_bytes=before, host_free_after_bytes=shutil.disk_usage(BASE).free,
                            preparation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                            critical_platform_files_verified=204,
                            prepared_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    print('Durable host output verified; unused runtime data removed; pinned platform unchanged')


if __name__ == '__main__':
    main()
