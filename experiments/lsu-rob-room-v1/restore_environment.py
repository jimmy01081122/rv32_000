#!/usr/bin/env python3
"""Restore the exact parked tool images and historical raw caches after native review."""
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').is_file())
BASE = ROOT/'build/experiments/lsu-rob-room-v1'
sys.path.insert(0, str(ROOT/'experiments/lsu-rob-room-v1'))
from publish_native import DOCKER, CONTAINER, verify
sys.path.insert(0, str(ROOT/'experiments/optimization-135-v1'))
from checkpoint import atomic_json

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

def main():
    output = BASE/'environment-restoration.json'
    require(not output.exists(), 'preserve earlier restoration receipt')
    require(json.loads((BASE/'physical-review.json').read_text())['passed'], 'physical review required')
    publication = json.loads((BASE/'native/native-publication.json').read_text())
    require(publication['passed'], 'completed host publication required')
    verify(BASE/'native', publication['files'])
    parked = json.loads((BASE/'temporary-capacity.json').read_text())
    archive = ROOT/parked['image_backup']
    require(parked['passed'] and sha(archive) == parked['image_backup_sha256'], 'image backup changed')
    state = dict(passed=False, script_sha256=sha(Path(__file__)),
                 started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), stages=[])
    atomic_json(output, state)
    def run(name, command):
        log = BASE/('restore-'+name+'.log')
        with log.open('x') as stream:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        state['stages'].append(dict(name=name, command=command, returncode=result.returncode,
                                    log_sha256=sha(log)))
        atomic_json(output, state)
        require(result.returncode == 0, 'restoration failed: '+name)
    jobs = subprocess.check_output(DOCKER+['top', CONTAINER, '-eo', 'pid,comm'], text=True).splitlines()
    require(not any(x.split()[-1] in ('openroad','yosys','make','python3') for x in jobs[1:]), 'native job still active')
    run('platform', DOCKER+['exec', CONTAINER, 'sha256sum', '--strict', '--quiet', '-c',
        '/workspace/docs/evidence/2026-10-18/post-lsu-baseline-preparation/environment/physical-tool-platform-sha256.txt'])
    run('native-stop', DOCKER+['stop', '--time', '10', CONTAINER])
    run('native-remove', DOCKER+['rm', CONTAINER])
    require(shutil.disk_usage(ROOT).free >= 5*1024**3, 'insufficient capacity for exact image restoration')
    run('images', DOCKER+['load', '--input', str(archive)])
    for tag, expected in parked['images'].items():
        actual = subprocess.check_output(DOCKER+['image', 'inspect', tag, '--format', '{{.Id}}'], text=True).strip()
        require(actual == expected, 'restored image identity differs: '+tag)
    restored = []
    seen = {}
    for row in parked['historical_files']:
        path, compressed = ROOT/row['path'], ROOT/row['gzip']
        require(sha(compressed) == row['gzip_sha256'], 'compressed historical data changed')
        require(not path.exists(), 'historical restore target unexpectedly exists')
        if row['sha256'] in seen:
            os.link(seen[row['sha256']], path)
        else:
            temporary = path.with_name(path.name+'.restore-tmp')
            with gzip.open(compressed, 'rb') as source, temporary.open('xb') as target:
                shutil.copyfileobj(source, target)
            require(temporary.stat().st_size == row['bytes'] and sha(temporary) == row['sha256'], 'decoded cache differs')
            os.replace(temporary, path)
        require(path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], 'restored bytes differ')
        seen[row['sha256']] = path
        restored.append(dict(path=row['path'], bytes=row['bytes'], sha256=row['sha256']))
    require(not subprocess.check_output(['git','status','--porcelain'], cwd=ROOT), 'tracked sources changed')
    state.update(passed=True, images=parked['images'], historical_files=restored,
                 native_runtime_removed=True, free_bytes=shutil.disk_usage(ROOT).free,
                 temporary_capacity_receipt_sha256=sha(BASE/'temporary-capacity.json'),
                 finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    atomic_json(output, state)
    print('Exact parked images and all eight historical raw caches restored')

if __name__ == '__main__':
    main()
