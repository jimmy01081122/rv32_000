#!/usr/bin/env python3
"""Restore archived ROOM build files to their original paths in this checkout."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile

from verify_completion_archive import Parts, verify

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/experiments/lsu-rob-room-v1'
DEFAULT = ROOT/'docs/evidence/2026-11-23/lsu-rob-room-complete'
CACHES = {'native', 'checkpoints', 'mapping-v1', 'shared-linked-v1', 'interrupted-parent-sta-v1'}

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def target(name, prefix):
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('unexpected archive path: '+name)
    path = prefix/relative
    if not path.resolve().is_relative_to(BASE.resolve()) or path.is_symlink() or path.parent.resolve() != path.parent:
        raise ValueError('unexpected target or symbolic link: '+name)
    return path

def store(tar, member, out, expected, reuse):
    if not member.isfile():
        raise ValueError('expected a regular file: '+member.name)
    key = (expected, member.mode & 0o777)
    if out.exists():
        if not out.is_file() or sha(out) != expected:
            raise ValueError('existing cache file differs: '+str(out))
        if out.stat().st_uid == os.getuid() and out.stat().st_mode & 0o777 == key[1]:
            reuse[key] = out
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    if key in reuse:
        os.link(reuse[key], out)
        return
    with tempfile.NamedTemporaryFile(dir=out.parent, delete=False) as temp:
        tmp = Path(temp.name)
    try:
        with tar.extractfile(member) as source, tmp.open('wb') as stream:
            while block := source.read(1024*1024):
                stream.write(block)
        if tmp.stat().st_size != member.size or sha(tmp) != expected:
            raise ValueError('decoded cache file differs: '+member.name)
        tmp.chmod(member.mode & 0o777)
        os.link(tmp, out)
        reuse[key] = out
    finally:
        tmp.unlink(missing_ok=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=DEFAULT)
    bundle = parser.parse_args().bundle.resolve()
    verify(bundle)
    inventory = json.loads((bundle/'copy-inventory.json').read_text())
    base = BASE.relative_to(ROOT)
    selected = {}
    for row in inventory['records']:
        p = Path(row['member'])
        if p.is_relative_to(base) and p.relative_to(base).parts[0] in CACHES:
            selected[row['member']] = row
    seen = set()
    reuse = {}
    with Parts([bundle/r['path'] for r in inventory['parts']]) as raw, io.BufferedReader(raw) as stream:
        with tarfile.open(fileobj=stream, mode='r|gz') as tar:
            for member in tar:
                if member.name in selected:
                    path = target(member.name, ROOT)
                    store(tar, member, path, selected[member.name]['sha256'], reuse)
                    seen.add(member.name)
    if seen != set(selected):
        raise ValueError('incomplete archive')
    for receipt in sorted((BASE/'checkpoints').glob('physical-ROOM-v*-checkpoint.json')):
        checkpoint = json.loads(receipt.read_text())
        archive = receipt.parent/checkpoint['archive']
        if sha(archive) != checkpoint['sha256']:
            raise ValueError('changed checkpoint')
        rows = {r['path']:r for r in checkpoint['records']}
        with tarfile.open(archive, 'r|gz') as tar:
            for member in tar:
                row = rows.pop(member.name)
                if row['kind'] == 'file':
                    path = target(member.name, BASE/'native')
                    store(tar, member, path, row['sha256'], reuse)
                elif row['kind'] == 'symlink':
                    # The only construction link connects hold repair back to its GRT parent.
                    if (row['path'], row['target']) != ('physical-ROOM-v2/grt', '../physical-ROOM-v1/grt'):
                        raise ValueError('unexpected checkpoint link')
                    path = BASE/'native'/row['path']
                    if not path.is_symlink():
                        path.symlink_to(row['target'], target_is_directory=True)
                    if os.readlink(path) != row['target']:
                        raise ValueError('changed checkpoint link')
                else:
                    target(member.name, BASE/'native').mkdir(parents=True, exist_ok=True)
        if rows:
            raise ValueError('checkpoint records missing')
    print('Restored and verified ROOM mapping, checkpoints, native stages and timing reports.')

if __name__ == '__main__':
    main()
