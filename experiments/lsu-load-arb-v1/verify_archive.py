#!/usr/bin/env python3
"""Verify public files and every decoded arbitration evidence member without extracting."""
import argparse,hashlib,json,tarfile
from pathlib import Path,PurePosixPath
def require(ok,message):
    if not ok:raise ValueError(message)
def digest(stream):
    h=hashlib.sha256()
    for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()
def verify(directory):
    sums={}
    for line in (directory/'SHA256SUMS').read_text().splitlines():
        h,name=line.split('  ',1);require(Path(name).name==name and name not in sums,'invalid checksum entry');sums[name]=h
    require(set(sums)=={p.name for p in directory.iterdir() if p.name!='SHA256SUMS'},'public file set differs')
    for name,h in sums.items():
        p=directory/name;require(p.is_file() and not p.is_symlink(),'unexpected public file type')
        with p.open('rb') as f:require(digest(f)==h,'public hash differs: '+name)
    inventory=json.loads((directory/'inventory.json').read_text());require(inventory['passed'],'archive not admitted')
    name=inventory['archive'];require(Path(name).name==name,'unsafe archive name');archive=directory/name
    require(archive.stat().st_size==inventory['archive_bytes'] and sums[name]==inventory['archive_sha256'],'archive identity differs')
    expected={r['path']:r for r in inventory['records']};require(len(expected)==len(inventory['records']),'duplicate inventory');seen=set();size=0
    with tarfile.open(archive,'r|gz') as tar:
        for m in tar:
            path=PurePosixPath(m.name)
            require(not path.is_absolute() and '..' not in path.parts and m.isfile() and m.name in expected and m.name not in seen,'unexpected member')
            row=expected[m.name];require(m.size==row['bytes'],'decoded size differs')
            with tar.extractfile(m) as f:require(digest(f)==row['sha256'],'decoded hash differs: '+m.name)
            seen.add(m.name);size+=m.size
    require(seen==set(expected),'missing member')
    return dict(passed=True,members=len(seen),decoded_bytes=size,archive_sha256=inventory['archive_sha256'],scope='archive integrity; candidate physical qualification remains separate')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);print(json.dumps(verify(p.parse_args().directory.resolve()),indent=2))
