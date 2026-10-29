"""Durably finish native repair/STA stages once their explicit prerequisites pass."""
from pathlib import Path
import datetime,hashlib,json,subprocess,time,concurrent.futures
ROOT=Path.cwd();BASE=ROOT/'build/experiments/lsu-b-validation-v2';DOCKER=['env','-u','DOCKER_HOST','-u','DOCKER_CONTEXT','-u','DOCKER_TLS','-u','DOCKER_TLS_VERIFY','-u','DOCKER_CERT_PATH','docker','--host=unix:///var/run/docker.sock'];CONTAINER='rv32-lsu-b-validation-v2';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
EXPECTED='f2c8b45';PERIODS=[9700,9800,9900,10000,10100,10200]
def save(path,data):
 temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,indent=2)+'\n');temp.replace(path)
def await_flag(path,flag,timeout):
 deadline=time.monotonic()+timeout
 while time.monotonic()<deadline:
  if path.exists() and json.loads(path.read_text()).get(flag):return
  time.sleep(15)
 raise TimeoutError('prerequisite did not complete: '+str(path))
def execute(command,log):
 with log.open('x') as out:run=subprocess.run(command,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
 return dict(command=command,returncode=run.returncode,log_sha256=sha(log))
def finish(variant):
 state=dict(variant=variant,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),records=[],complete=False);status=BASE/('finish-'+variant+'.json');save(status,state)
 try:
  if variant=='baseline':
   await_flag(BASE/'physical-baseline-v1/pipeline.json','grt_complete',7200)
   assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).startswith(EXPECTED)
   command=DOCKER+['exec','--user','1000:1000',CONTAINER,'python3','/workspace/experiments/lsu-b-validation-v2/repair.py','--variant','baseline','--incoming','/workspace/build/experiments/lsu-b-validation-v2/physical-baseline-v1/grt','--output','/workspace/build/experiments/lsu-b-validation-v2/physical-baseline-v2']
   row=execute(command,BASE/'physical-baseline-v2-controller.log');state['records'].append(row);save(status,state);assert row['returncode']==0
  attempt=BASE/('physical-'+variant+'-v2');await_flag(attempt/'pipeline.json','complete',4200)
  command=['python3','experiments/lsu-b-validation-v2/analyze_physical.py','--attempt',str(attempt/'eco'),'--container',CONTAINER,'--adder-audit','build/baseline-setup/asap7-adder-qualification-v2/summary.json','--label','independent-sta-v1','--periods-ps',*map(str,PERIODS)]
  row=execute(command,BASE/('sta-'+variant+'-v1-controller.log'));state['records'].append(row);save(status,state);assert row['returncode']==0;state['complete']=True
 except Exception as e:state['error']=repr(e)
 finally:state['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save(status,state);print(variant,json.dumps(state),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 futures=[pool.submit(finish,v) for v in ['B','baseline']]
 for f in futures:f.result()
