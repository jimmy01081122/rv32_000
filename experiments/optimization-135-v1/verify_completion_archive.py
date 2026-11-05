#!/usr/bin/env python3
"""Verify split A evidence and every decoded member without extracting files."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(stream):
    result = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        result.update(block)
    return result.hexdigest()


class Parts(io.RawIOBase):
    def __init__(self, paths):
        self.paths = iter(paths)
        self.current = None

    def readable(self):
        return True

    def readinto(self, buffer):
        while True:
            if self.current is None:
                path = next(self.paths, None)
                if path is None:
                    return 0
                self.current = path.open('rb')
            count = self.current.readinto(buffer)
            if count:
                return count
            self.current.close()
            self.current = None

    def close(self):
        if self.current is not None:
            self.current.close()
        super().close()


def verify(directory):
    sums = {}
    for line in (directory / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split('  ', 1)
        require(Path(name).name == name and name not in sums, 'invalid checksum entry')
        sums[name] = expected
    require(set(sums) == {p.name for p in directory.iterdir() if p.name != 'SHA256SUMS'},
            'public archive file set differs')
    for name, expected in sums.items():
        path = directory / name
        require(path.is_file() and not path.is_symlink(), 'unexpected archive file type')
        with path.open('rb') as stream:
            require(digest(stream) == expected, 'public file checksum differs: ' + name)
    inventory = json.loads((directory / 'copy-inventory.json').read_text())
    require(inventory['passed'], 'archive was not admitted')
    parts = inventory['parts']
    require([p['path'] for p in parts] ==
            [f'A-completion.tar.gz.part-{i:03d}' for i in range(len(parts))],
            'parts are missing or unordered')
    aggregate = hashlib.sha256()
    stored = 0
    for part in parts:
        path = directory / part['path']
        require(path.stat().st_size == part['bytes'] and sums[path.name] == part['sha256'],
                'part identity differs')
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                aggregate.update(block)
                stored += len(block)
    require(stored == inventory['archive_bytes'] and
            aggregate.hexdigest() == inventory['archive_sha256'], 'joined archive differs')
    rows = {r['member']: r for r in inventory['records']}
    require(len(rows) == len(inventory['records']), 'duplicate inventory member')
    seen = set()
    decoded = 0
    with Parts([directory / p['path'] for p in parts]) as raw:
        with io.BufferedReader(raw) as stream:
            with tarfile.open(fileobj=stream, mode='r|gz') as tar:
                for member in tar:
                    path = PurePosixPath(member.name)
                    require(not path.is_absolute() and '..' not in path.parts and
                            member.name in rows and member.name not in seen and member.isfile(),
                            'unexpected/duplicate archive member: ' + member.name)
                    row = rows[member.name]
                    require(member.size == row['bytes'], 'decoded size differs')
                    with tar.extractfile(member) as payload:
                        require(digest(payload) == row['sha256'], 'decoded hash differs: ' + member.name)
                    seen.add(member.name)
                    decoded += member.size
    require(seen == set(rows), 'missing archive members')
    return dict(passed=True, parts=len(parts), members=len(seen), decoded_bytes=decoded,
                archive_sha256=inventory['archive_sha256'],
                scope='archive integrity; functional/physical admission is recorded separately inside the bundle')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory.resolve()), indent=2))
