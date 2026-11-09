"""Read the running container mount namespace and verify a streamed tar copy."""
import hashlib
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile


def stream_copy(docker, container, guest, destination, rows):
    expected = {row['path']: row for row in rows}
    if len(expected) != len(rows):
        raise ValueError('duplicate publication inventory')
    seen, links = set(), []
    destination = Path(destination)
    def path_for(name):
        if name.startswith('./'):
            name = name[2:]
        name = name.rstrip('/')
        if name not in expected or Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('unexpected streamed member: '+name)
        path = destination/name
        for parent in path.parents:
            if parent == destination:
                break
            if parent.is_symlink():
                raise ValueError('stream destination traverses a symlink')
        return name, path
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(docker+['exec', container, 'tar', '-C', guest, '-cf', '-', '.'],
                                   stdout=subprocess.PIPE, stderr=errors)
        try:
            with tarfile.open(fileobj=process.stdout, mode='r|') as tar:
                for member in tar:
                    if member.name in ('.', './'):
                        if not member.isdir():
                            raise ValueError('invalid stream root')
                        continue
                    name, path = path_for(member.name)
                    if name in seen:
                        raise ValueError('duplicate streamed member')
                    seen.add(name)
                    row = expected[name]
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if row['kind'] == 'directory':
                        if not member.isdir():
                            raise ValueError('stream directory type differs')
                        path.mkdir(exist_ok=True)
                    elif row['kind'] == 'symlink':
                        if not member.issym() or member.linkname != row['target']:
                            raise ValueError('stream symlink differs')
                        if path.is_symlink():
                            if os.readlink(path) != row['target']:
                                raise ValueError('existing symlink differs')
                        else:
                            path.symlink_to(row['target'])
                    elif member.islnk():
                        target_name, target = path_for(member.linkname)
                        other = expected[target_name]
                        if other['kind'] != 'file' or (row['bytes'], row['sha256']) != (other['bytes'], other['sha256']):
                            raise ValueError('hardlink content identities differ')
                        links.append((path, target))
                    elif member.isfile() and member.size == row['bytes']:
                        temporary = path.with_name(path.name+'.publish-partial')
                        if path.is_symlink() or temporary.exists():
                            raise ValueError('unexpected destination link or partial file')
                        h = hashlib.sha256()
                        existing = path.exists()
                        with tar.extractfile(member) as source:
                            output = None if existing else temporary.open('xb')
                            try:
                                for block in iter(lambda: source.read(1048576), b''):
                                    h.update(block)
                                    if output:
                                        output.write(block)
                                if output:
                                    output.flush()
                                    os.fsync(output.fileno())
                            finally:
                                if output:
                                    output.close()
                        if h.hexdigest() != row['sha256']:
                            raise ValueError('streamed content hash differs: '+name)
                        if not existing:
                            os.chmod(temporary, member.mode & 0o777)
                            os.replace(temporary, path)
                    else:
                        raise ValueError('stream member type/size differs: '+name)
            process.stdout.close()
            status = process.wait()
            if status:
                errors.seek(0)
                raise ValueError('native tar failed: '+errors.read().decode(errors='replace'))
            if seen != set(expected):
                raise ValueError('stream omitted inventoried files')
            while links:
                remaining = []
                for path, target in links:
                    if not target.is_file() or target.is_symlink():
                        remaining.append((path, target))
                    elif not path.exists():
                        os.link(target, path)
                if len(remaining) == len(links):
                    raise ValueError('unresolved stream hardlinks')
                links = remaining
        except BaseException:
            if process.poll() is None:
                process.terminate()
            process.wait()
            raise
