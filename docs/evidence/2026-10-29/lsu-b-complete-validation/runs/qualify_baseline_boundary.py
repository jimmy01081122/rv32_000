"""Refine a measured baseline clock boundary only with fresh native corner trials."""
from pathlib import Path
import datetime,hashlib,json,math,subprocess,time
ROOT=Path.cwd();BASE=ROOT/'build/experiments/lsu-b-validation-v2';stage=BASE/'physical-baseline-v2/eco';status=BASE/'baseline-boundary-selection.json';report=dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),state='waiting-for-initial-baseline-STA',records=[],passed=False);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save():status.write_text(json.dumps(report,indent=2)+'\n')
save()
try:
 analysis=stage/'independent-sta-v1';deadline=time.monotonic()+7200
 while not (analysis/'closure-review.json').exists():
  if time.monotonic()>deadline:raise TimeoutError('baseline initial collection not completed')
  time.sleep(15)
 for iteration in range(3):
  review=json.loads((analysis/'closure-review.json').read_text());collection=json.loads((analysis/'run.json').read_text());assert review['passed'],'baseline has no qualified period'
  minimum=review['smallest_tested_passing_period_ps'];periods=collection['clock_trials_ps']
  if minimum-100 in periods:break
  # Slack only guides which points to execute; it never establishes a passing period.
  sample=next(r for r in review['records'][0]['trials'] if r['period_ps']==minimum)
  slack=min(next(r for r in corner['trials'] if r['period_ps']==minimum)['setup_slack_ps'] for corner in review['records'])
  estimate=max(2400,math.ceil((minimum-slack)/100)*100);trials=sorted({estimate-100,estimate,minimum,10000});label=f'independent-boundary-v{iteration+2}'
  command=['python3','experiments/lsu-b-validation-v2/analyze_physical.py','--attempt',str(stage),'--container','rv32-lsu-b-validation-v2','--adder-audit','build/baseline-setup/asap7-adder-qualification-v2/summary.json','--label',label,'--periods-ps',*map(str,trials)];log=BASE/f'sta-baseline-boundary-v{iteration+2}-controller.log'
  report['state']='collecting-actual-boundary';save()
  with log.open('x') as stream:r=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
  report['records'].append(dict(command=command,returncode=r.returncode,log_sha256=sha(log)));save();assert r.returncode==0;analysis=stage/label
 else:raise RuntimeError('boundary still needs additional measured neighbor')
 assert minimum-100 in periods and 10000 in review['qualified_periods_ps'];report.update(state='finished',passed=True,selected_analysis=str(analysis.relative_to(ROOT)),qualified_periods_ps=review['qualified_periods_ps'],smallest_tested_passing_period_ps=minimum,closure_review_sha256=sha(analysis/'closure-review.json'))
except Exception as e:report.update(state='blocked',error=repr(e))
finally:report['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save();print(json.dumps(report,indent=2),flush=True)
