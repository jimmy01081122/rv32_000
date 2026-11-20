#!/usr/bin/env python3
"""Measure all frozen workloads at the independently qualified minimum period."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').is_file())
BASE = ROOT/'build/experiments/lsu-rob-room-v1'
sys.path.insert(0, str(ROOT/'scripts'))
from build_experiment_sim import state

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    output = BASE/'fastest-driver.json'
    if output.exists():
        raise ValueError('preserve earlier fastest driver receipt')
    physical_path = BASE/'physical-review.json'
    physical = json.loads(physical_path.read_text())
    if not physical['passed']:
        raise ValueError('independent physical qualification required')
    period = physical['ROOM_physical']['smallest_tested_passing_period_ps']
    if period not in physical['ROOM_physical']['qualified_periods_ps']:
        raise ValueError('unqualified clock point')
    measurement = BASE/f'measurement-{period}ps-v1'
    commands = []
    if period != 10000:
        commands.append(('measurement', ['python3','scripts/measure_cpu_experiment.py',
            '--experiment','experiments/lsu-rob-room-v1/manifest.json',
            '--build-summary',str(BASE/'build-v1/summary.json'), '--out',str(measurement),
            '--period-ps',str(period)]))
    commands.append(('review', ['python3','experiments/lsu-rob-room-v1/review_measurement.py',
        '--measurement',str(measurement), '--output',str(BASE/'fastest-review.json')]))
    start = state()
    if start['status']:
        raise ValueError('clean committed inputs required')
    record = dict(complete=False, start=start, period_ps=period, memory_ps=10000,
                  started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  driver_sha256=sha(Path(__file__)), physical_review_sha256=sha(physical_path), steps=[])
    def save():
        output.write_text(json.dumps(record, indent=2)+'\n')
    save()
    for name, command in commands:
        log = BASE/('fastest-'+name+'.log')
        with log.open('x') as stream:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        record['steps'].append(dict(name=name, command=command, returncode=result.returncode,
                                    log_sha256=sha(log)))
        save()
        print(name, result.returncode, flush=True)
        if result.returncode:
            return result.returncode
    record.update(end=state(), finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    record['complete'] = (record['end'] == start and sha(physical_path) == record['physical_review_sha256']
                          and sha(Path(__file__)) == record['driver_sha256'])
    save()
    return 0 if record['complete'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
