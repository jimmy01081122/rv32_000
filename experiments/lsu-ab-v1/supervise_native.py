#!/usr/bin/env python3
"""Record the observed native controller exit on durable workspace storage."""
import datetime
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'experiments/optimization-135-v1'))
from checkpoint import atomic_json


def main():
    if ROOT != Path('/workspace'):
        raise ValueError('run inside the pinned native container')
    base = ROOT/'build/experiments/lsu-ab-v1'
    outputs = [base/'native/native-exit.json', base/'checkpoints/native-exit.json']
    if any(p.exists() for p in outputs):
        raise ValueError('preserve previous exit receipts')
    command = ['python3', str(Path(__file__).with_name('run_physical.py')), '--label', 'v1']
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(command, cwd=ROOT)
    record = dict(command=command, returncode=result.returncode, started_utc=started,
                  finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  supervisor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    for output in outputs:
        atomic_json(output, record)
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
