import json,subprocess,time,datetime,math,hashlib,sys
from pathlib import Path
ROOT=Path('/workspace/rv32_000');OUT=ROOT/'build/experiments/lsu-a-v1';STATE=OUT/'physical-pipeline.json';state={'scope':'isolated A fixed baseline physical flow and actual timing-grid collection','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'commands':[],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'complete':False}
def save():STATE.write_text(json.dumps(state,indent=2)+'\n')
def say(*args):print(datetime.datetime.now(datetime.timezone.utc).isoformat(),*args,flush=True)
def run(args,label,allow_failure=False):
 log=OUT/(label+'-driver.log');assert not log.exists()
 row={'command':args,'driver_log':str(log.relative_to(ROOT)),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};state['commands'].append(row);save();say('launch',label)
 with log.open('w') as f:p=subprocess.run(args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
 row.update(returncode=p.returncode,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),driver_log_sha256=hashlib.sha256(log.read_bytes()).hexdigest());save()
 if p.returncode and not allow_failure:raise RuntimeError((label,p.returncode,log.read_text()[-2000:]))
def wait(directory):
 state['active_attempt']=str(directory.relative_to(ROOT));save();last=None;last_time=0
 while True:
  row=json.loads((directory/'run.json').read_text());log=directory/'make.log';text=log.read_text(errors='replace') if log.exists() else '';line=text.splitlines()[-1] if text.splitlines() else '(no log yet)'
  if time.monotonic()-last_time>=55:say(directory.name,row.get('job_state'),line[-200:]);last_time=time.monotonic()
  if row.get('job_state')=='finished':
   assert row['returncode']==0 and row['flow_completed'] and row['input_identities_unchanged'],row
   say(directory.name,'completed with unchanged inputs');return
  time.sleep(15)
common=['python3','scripts/run_baseline_physical.py','--experiment','experiments/lsu-a-v1/manifest.json','--output-root','build/experiments/lsu-a-v1','--lowered-rtl','build/experiments/lsu-a-v1/rtl_lowered.v','--container','rv32-lsu-a-physical','--adder-mapping','abc','--jobs','2','--detached']
def analyze(attempt,label,periods):
 args=['python3','scripts/analyze_baseline_physical.py','--experiment','experiments/lsu-a-v1/manifest.json','--attempt',str(attempt.relative_to(ROOT)),'--container','rv32-lsu-a-physical','--adder-audit','build/baseline-setup/asap7-adder-qualification-v2/summary.json','--label',label,'--periods-ps',*map(str,periods)]
 run(args,label);directory=attempt/label
 run(['python3','scripts/check_physical_closure.py','--analysis',str(directory.relative_to(ROOT))],label+'-review',allow_failure=True)
 review=json.loads((directory/'closure-review.json').read_text());assert 'error' not in review,review;return review
try:
 save();synth=OUT/'physical-5500ps-synth-clean-v1';wait(synth)
 backend=OUT/'physical-14000ps-backend-clean-v1';run(common+['--period-ps','14000','--label','backend-clean-v1','--synthesis-from',str(synth.relative_to(ROOT))],'backend-launch');wait(backend)
 eco=OUT/'physical-14000ps-eco-clean-v1';run(common+['--period-ps','14000','--label','eco-clean-v1','--grt-from',str(backend.relative_to(ROOT))],'eco-launch');wait(eco)
 initial=analyze(eco,'initial-14000ps',[14000]);assert initial['passed']
 min_slack=min(r['trials'][0]['setup_slack_ps'] for r in initial['records']);guess=int(math.ceil((14000-min_slack)/100))*100
 state.update(boundary_seed_from_slack_ps=guess,seed_role='trial scheduling only, not an achieved clock claim');save()
 periods=sorted({guess-100,guess,10000});assert min(periods)>2200
 for version in range(1,7):
  label='boundary-v'+str(version);review=analyze(eco,label,periods);p=review['smallest_tested_passing_period_ps']
  if p is not None and p-100 in periods and p-100 not in review['qualified_periods_ps']:
   state.update(complete=True,selected_analysis=str((eco/label).relative_to(ROOT)),smallest_tested_passing_period_ps=p,common_10000ps_qualified=10000 in review['qualified_periods_ps'],finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());save();say('actual boundary qualified',p,'common10000',state['common_10000ps_qualified']);break
  p=(p if p is not None else max(periods)+100);periods=sorted({p-100,p,10000});say('need another actual boundary trial',periods)
 else:raise RuntimeError('six actual boundary collections failed to bracket; preserve all attempts for review')
except BaseException as error:
 state.update(error=repr(error),finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());save();raise
