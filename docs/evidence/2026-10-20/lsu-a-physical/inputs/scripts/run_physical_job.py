#!/usr/bin/env python3
"""Durable container worker: preserve real exit status and input identities."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2)+'\n')
    temporary.replace(path)


def execute(spec_path):
    spec = json.loads(spec_path.read_text())
    report_path = Path(spec['report'])
    log_path = Path(spec['log'])
    lock_path = report_path.parent/'job.lock'
    with lock_path.open('x') as lock:
        lock.write(str(os.getpid())+'\n')
    report = json.loads(report_path.read_text())
    report.update(job_state='running', job_pid=os.getpid(), started_utc=now(),
                  flow_completed=False, passed=False)
    write_json(report_path, report)
    def mismatches():
        return [name for name, expected in spec['inputs'].items()
                if not Path(name).is_file() or digest(name)!=expected]
    try:
        changed = mismatches()
        if changed:
            raise ValueError('job inputs changed before launch: '+', '.join(changed))
        with log_path.open('w') as log:
            result = subprocess.run(spec['command'], cwd=spec['cwd'],
                                    stdout=log, stderr=subprocess.STDOUT)
        changed = mismatches()
        report.update(returncode=result.returncode, input_mismatches=changed,
                      input_identities_unchanged=not changed,
                      flow_completed=result.returncode==0 and not changed,
                      job_state='finished')
    except Exception as error:
        report.update(job_state='failed', worker_error=str(error), flow_completed=False)
        with log_path.open('a') as log:
            traceback.print_exc(file=log)
    finally:
        report.update(finished_utc=now(), passed=False)
        if log_path.exists():
            report['log_sha256'] = digest(log_path)
        write_json(report_path, report)
    return 0 if report['flow_completed'] else 1


if __name__=='__main__':
    raise SystemExit(execute(Path(sys.argv[1])))
