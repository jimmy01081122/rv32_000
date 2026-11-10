#!/usr/bin/env python3
"""Run native AB construction, durability verification and independent corners."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT/'build/experiments/lsu-ab-v1'
sys.path.insert(0, str(ROOT/'experiments/optimization-135-v1'))
from checkpoint import atomic_json
from publish_native import DOCKER, CONTAINER


def main():
    output = BASE/'physical-driver.json'
    if output.exists():
        raise ValueError('preserve previous driver receipt')
    native = BASE/'native'
    audit = ROOT/'build/baseline-setup/asap7-adder-qualification-v2/summary.json'
    guard = native/'physical-AB-v4/guard'
    periods = list(map(str, range(9000, 10001, 100)))
    common = ['--container', CONTAINER, '--adder-audit', str(audit)]
    commands = [
        ('native', DOCKER+['exec', '--user', '1000:1000', '-w', '/workspace', CONTAINER,
                           'python3', '/workspace/experiments/lsu-ab-v1/supervise_native.py']),
        ('publication', ['python3', str(HERE/'publish_native.py')]),
        ('parent-sta', ['python3', str(ROOT/'build/experiments/lsu-b-validation-v2/analyze_physical_v2.py'),
                        '--attempt', str(native/'physical-AB-v2/eco'), '--label', 'independent-sta-v1',
                        '--contract', str(HERE/'contract-hold40.json'), *common, '--periods-ps', *periods]),
        ('guard-sta', ['python3', str(ROOT/'experiments/lsu-b-validation-v2/analyze_guard.py'),
                       '--attempt', str(guard), '--label', 'independent-boundary-v1',
                       '--contract', str(native/'AB-guard-bound-contract.json'), *common, '--periods-ps', *periods]),
        ('review', ['python3', str(HERE/'review_physical.py'), '--analysis', str(guard/'independent-boundary-v1'),
                    '--output', str(BASE/'physical-review.json')])]
    record = dict(scope='native construction and independent review; workload timing still separate',
                  started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  stages=[], complete=False)
    atomic_json(output, record)
    for name, command in commands:
        log = BASE/('physical-'+name+'.log')
        with log.open('x') as stream:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        record['stages'].append(dict(stage=name, command=command, returncode=result.returncode,
                                     log=log.name, log_sha256=hashlib.sha256(log.read_bytes()).hexdigest()))
        atomic_json(output, record)
        print(name, result.returncode, flush=True)
        if result.returncode:
            return result.returncode
    record.update(complete=True, finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    atomic_json(output, record)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
