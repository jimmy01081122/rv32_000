import json,subprocess,time,datetime
from pathlib import Path
root=Path('/workspace/rv32_000');out=root/'build/experiments/lsu-b-v1'
last=0
while True:
 r=json.loads((out/'functional-worker-v1/run.json').read_text())
 if r['job_state']=='finished':
  assert r['returncode']==0 and r['flow_completed'] and r['input_identities_unchanged'],r
  break
 assert r['job_state'] in ['queued','running'],r
 if time.monotonic()-last>55:print(datetime.datetime.now(datetime.timezone.utc).isoformat(),'waiting for complete functional/full27 run',flush=True);last=time.monotonic()
 time.sleep(10)
for script in ['transition-to-physical.py','physical-pipeline.py']:
 result=subprocess.run(['python3',str(out/script)],cwd=root)
 if result.returncode:raise SystemExit(result.returncode)
