"""Collect actual corners after each completed common input guard; never waive failure."""
from pathlib import Path
import concurrent.futures,datetime,hashlib,json,subprocess,time
ROOT=Path.cwd();BASE=ROOT/'build/experiments/lsu-b-validation-v2';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def finish(variant,periods):
 path=BASE/('finish-guard-'+variant+'.json');state=dict(variant=variant,state='waiting',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),complete=False)
 def save():path.write_text(json.dumps(state,indent=2)+'\n')
 save()
 try:
  attempt=BASE/('physical-'+variant+'-v4');deadline=time.monotonic()+4000
  while not (attempt/'pipeline.json').exists() or not json.loads((attempt/'pipeline.json').read_text())['complete']:
   report=attempt/'guard/run.json'
   if report.exists() and json.loads(report.read_text()).get('job_state')=='finished' and json.loads(report.read_text()).get('returncode')!=0:raise RuntimeError('guard native construction failed')
   if time.monotonic()>deadline:raise TimeoutError('guard did not complete')
   time.sleep(10)
  command=['python3','experiments/lsu-b-validation-v2/analyze_guard.py','--attempt',str(attempt/'guard'),'--container','rv32-lsu-b-validation-v2','--adder-audit','build/baseline-setup/asap7-adder-qualification-v2/summary.json','--label','independent-boundary-v1','--periods-ps',*map(str,periods)];log=BASE/('sta-guard-'+variant+'-controller.log');state.update(state='collecting',command=command);save()
  with log.open('x') as stream:r=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
  state.update(returncode=r.returncode,log_sha256=sha(log));assert r.returncode==0;closure=attempt/'guard/independent-boundary-v1/closure-review.json';state.update(closure_review_sha256=sha(closure),timing_passed=json.loads(closure.read_text())['passed'],complete=True,state='finished')
 except Exception as e:state.update(state='blocked',error=repr(e))
 finally:state['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save();print(json.dumps(state),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 fs=[pool.submit(finish,'baseline',[9400,9500,9600,10000]),pool.submit(finish,'B',[9500,9600,9700,10000])]
 for f in fs:f.result()
