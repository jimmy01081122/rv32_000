"""Continue only after independently qualified B timing; preserve actual child exits."""
import datetime,hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path('/workspace/rv32_000');OUT=ROOT/'build/experiments/lsu-b-v1';STATE=OUT/'completion-pipeline.json';assert not STATE.exists()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
r={'scope':'exact-clock full27 and strict build/functional/physical review; no baseline promotion','started_utc':utc(),'script_sha256':sha(Path(__file__)),'commands':[],'complete':False}
def save():STATE.write_text(json.dumps(r,indent=2)+'\n')
def run(command,name,allow_failure=False):
 log=OUT/(name+'.log');assert not log.exists();row={'command':command,'started_utc':utc(),'log':str(log.relative_to(ROOT))};r['commands'].append(row);save()
 with log.open('w') as f:p=subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
 row.update(returncode=p.returncode,finished_utc=utc(),log_sha256=sha(log));save()
 if p.returncode and not allow_failure:raise RuntimeError((name,p.returncode))
 return p.returncode
try:
 save()
 while True:
  p=OUT/'physical-pipeline.json'
  if p.exists():
   physical=json.loads(p.read_text())
   if physical.get('error'):raise RuntimeError('physical pipeline failed: '+physical['error'])
   if physical.get('complete'):break
  time.sleep(10)
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
 period=physical['smallest_tested_passing_period_ps'];analysis=physical['selected_analysis'];r.update(period_ps=period,analysis=analysis,common_qualified=physical['common_10000ps_qualified']);save()
 if period!=10000:
  measurement=OUT/f'measurement-{period}ps-v1';worker=OUT/f'measurement-{period}ps-worker-v1';assert not measurement.exists() and not worker.exists();worker.mkdir()
  command=['python3','scripts/measure_cpu_experiment.py','--experiment','experiments/lsu-b-v1/manifest.json','--build-summary','build/experiments/lsu-b-v1/build-clean-v1/summary.json','--out',str(measurement.relative_to(ROOT)),'--period-ps',str(period)]
  initial=json.loads((OUT/'functional-worker-v1/job-spec.json').read_text());inputs=dict(initial['inputs'])
  build=json.loads((OUT/'build-clean-v1/summary.json').read_text());contract=json.loads((ROOT/'baselines/ap5b-post-lsu-v1/manifest.json').read_text())
  for item in build['executables'].values():
   for p in [ROOT/item['path'],(ROOT/item['path']).parent/'Vrv32_ooo_core__verFiles.dat']:inputs['/workspace/'+str(p.relative_to(ROOT))]=sha(p)
  for p in [OUT/'build-clean-v1/summary.json',OUT/'qualification-clean-v1/summary.json',*[ROOT/x['source_elf'] for x in contract['workloads']]]:inputs['/workspace/'+str(p.relative_to(ROOT))]=sha(p)
  guest='/workspace/'+str(worker.relative_to(ROOT));spec={'report':guest+'/run.json','log':guest+'/driver.log','cwd':'/workspace','command':command,'inputs':inputs}
  (worker/'job-spec.json').write_text(json.dumps(spec,indent=2)+'\n');(worker/'run.json').write_text(json.dumps({'job_state':'queued','passed':False,'created_utc':utc()},indent=2)+'\n')
  run(['docker','exec','-d','rv32-lsu-b-physical','python3','scripts/run_physical_job.py',guest+'/job-spec.json'],'fastest-worker-launch')
  queued=time.monotonic()
  while True:
   job=json.loads((worker/'run.json').read_text())
   if job['job_state']=='finished':
    assert job['returncode']==0 and job['flow_completed'] and job['input_identities_unchanged'],job;break
   assert job['job_state'] in ['queued','running'],job
   if job['job_state']=='queued' and time.monotonic()-queued>30:raise RuntimeError('new exclusive worker never entered running state')
   time.sleep(10)
  r.update(fastest_worker=str(worker.relative_to(ROOT)),fastest_worker_summary_sha256=sha(worker/'run.json'));save()
 else:
  measurement=OUT/'measurement-10000ps-v1';r['same_qualified_point_uses_existing_full27']=True;save()
 common=['python3','scripts/review_cpu_experiment.py','--experiment','experiments/lsu-b-v1/manifest.json','--build-summary','build/experiments/lsu-b-v1/build-clean-v1/summary.json','--qualification-summary','build/experiments/lsu-b-v1/qualification-clean-v1/summary.json','--analysis',analysis]
 for point,directory in [('common-clock',OUT/'measurement-10000ps-v1'),('fastest',measurement)]:
  target=OUT/('review-'+point+'-v1.json');command=common+['--measurement',str(directory.relative_to(ROOT)),'--comparison-point',point,'--out',str(target.relative_to(ROOT))]
  expected=point=='common-clock' and not physical['common_10000ps_qualified'];rc=run(command,'review-'+point+'-driver',expected);result=json.loads(target.read_text())
  if expected:assert rc!=0 and result.get('passed') is False and 'not independently qualified' in result.get('error',''),result
  else:assert rc==0 and result.get('passed') is True,result
 r.update(complete=True,finished_utc=utc(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_status=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True));assert not r['source_status'];save()
except BaseException as error:
 r.update(error=repr(error),finished_utc=utc());save();raise
