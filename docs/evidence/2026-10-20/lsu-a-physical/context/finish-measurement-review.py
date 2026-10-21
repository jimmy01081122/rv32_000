"""Monitor real job completion, then review without changing tracked source."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import time

ROOT = Path('/workspace/rv32_000')
EXP = ROOT/'build/experiments/lsu-a-v1'
REPORT = EXP/'measurement-9900ps-relaunch-v2/run.json'
OUT = EXP/'measurement-review-supervisor.json'
assert not OUT.exists()
state = {'scope':'Monitor the real worker; independent review runs only after unchanged inputs and exit zero.',
         'started_utc':datetime.now(timezone.utc).isoformat(),
         'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'commands':[], 'complete':False}

def save():
    OUT.write_text(json.dumps(state,indent=2)+'\n')

save()
try:
    while True:
        worker = json.loads(REPORT.read_text())
        summary = json.loads((EXP/'measurement-9900ps-v1/summary.json').read_text())
        records = summary['records']
        print(datetime.now(timezone.utc).isoformat(), 'worker',worker['job_state'],
              'cases',len(records),'passed',sum(r['passed'] for r in records),
              'last',records[-1]['name'] if records else None,flush=True)
        if worker['job_state'] in ['finished','failed']:
            assert worker['flow_completed'] and worker['returncode'] == 0
            assert worker['input_identities_unchanged'] and not worker['input_mismatches']
            assert summary['passed'] and len(records) == 27
            assert summary['start'] == summary['end'] and not summary['start']['status']
            break
        time.sleep(45)
    commands = [
        ['python3','scripts/review_cpu_experiment.py','--experiment','experiments/lsu-a-v1/manifest.json',
         '--measurement','build/experiments/lsu-a-v1/measurement-9900ps-v1',
         '--analysis','build/experiments/lsu-a-v1/physical-14000ps-eco-clean-v1/boundary-v1',
         '--comparison-point','fastest','--out','build/experiments/lsu-a-v1/review-fastest-v1.json'],
        ['python3','build/experiments/lsu-a-v1/analyze-operating-points.py']]
    for i, command in enumerate(commands):
        log = EXP/f'measurement-review-{i+1}.log'
        with log.open('x') as output:
            process = subprocess.run(command,cwd=ROOT,stdout=output,stderr=subprocess.STDOUT)
        state['commands'].append({'command':command,'returncode':process.returncode,
                                  'log':str(log.relative_to(ROOT)),
                                  'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
        save()
        assert process.returncode == 0, log.read_text()
        print(log.read_text(),flush=True)
    state['complete'] = True
except Exception as error:
    state['error'] = str(error)
    raise
finally:
    state['finished_utc'] = datetime.now(timezone.utc).isoformat()
    save()
