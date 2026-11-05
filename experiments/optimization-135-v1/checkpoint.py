#!/usr/bin/env python3
"""Save and verify completed native stages on a separate durable filesystem."""
import hashlib
import json
import os
from pathlib import Path
import tarfile


def digest(stream):
    h = hashlib.sha256()
    for block in iter(lambda: stream.read(1024*1024), b''):
        h.update(block)
    return h.hexdigest()


def atomic_json(path, data):
    path = Path(path)
    temporary = path.with_name(path.name+'.tmp')
    with temporary.open('x') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def verify_archive(archive, rows):
    expected = {r['path']: r for r in rows}
    if len(expected) != len(rows):
        raise ValueError('duplicate checkpoint entry')
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        if len(members) != len(rows) or {m.name for m in members} != set(expected):
            raise ValueError('checkpoint member set differs')
        for member in members:
            row = expected[member.name]
            if row['kind'] == 'file':
                if not member.isfile() or member.size != row['bytes']:
                    raise ValueError('checkpoint size/type differs')
                with tar.extractfile(member) as stream:
                    if digest(stream) != row['sha256']:
                        raise ValueError('checkpoint bytes differ')
            elif row['kind'] == 'symlink':
                if not member.issym() or member.linkname != row['target']:
                    raise ValueError('checkpoint link differs')
            elif not member.isdir():
                raise ValueError('checkpoint directory differs')


def checkpoint(directory, durable):
    directory, durable = Path(directory), Path(durable)
    output = durable/(directory.name+'.tar.gz')
    receipt = durable/(directory.name+'-checkpoint.json')
    if output.exists() or receipt.exists():
        raise ValueError('preserve existing checkpoint')
    rows = []
    for path in [directory, *sorted(directory.rglob('*'))]:
        row = {'path': str(path.relative_to(directory.parent))}
        if path.is_symlink():
            target = os.readlink(path)
            if Path(target).is_absolute() or not path.resolve(strict=True).is_relative_to(directory.parent):
                raise ValueError('checkpoint link leaves attempt')
            row.update(kind='symlink', target=target)
        elif path.is_file():
            with path.open('rb') as f:
                row.update(kind='file', bytes=path.stat().st_size, sha256=digest(f))
        elif path.is_dir():
            row.update(kind='directory')
        else:
            raise ValueError('unexpected checkpoint file type')
        rows.append(row)
    temporary = output.with_name(output.name+'.tmp')
    with temporary.open('xb') as f:
        with tarfile.open(fileobj=f, mode='w:gz', compresslevel=1, dereference=False) as tar:
            for row in rows:
                tar.add(directory.parent/row['path'], arcname=row['path'], recursive=False)
        f.flush()
        os.fsync(f.fileno())
    verify_archive(temporary, rows)
    os.replace(temporary, output)
    with output.open('rb') as f:
        archive_sha = digest(f)
    atomic_json(receipt, dict(passed=True, archive=output.name, sha256=archive_sha,
                             stored_bytes=output.stat().st_size, records=rows))
    return dict(archive=output.name, sha256=archive_sha, receipt=receipt.name)
