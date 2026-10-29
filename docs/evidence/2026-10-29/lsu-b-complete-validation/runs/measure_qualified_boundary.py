"""Measure full27 only after B's actual independent boundary passes strict review."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,subprocess,time
ROOT=Path.cwd();BASE=ROOT/'build/experiments/lsu-b-validation-v2';analysis=BASE/'physical-B-v2/eco/independent-boundary-v2';status=BASE/'qualified-boundary-measurement.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();report=dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),state='waiting-for-physical',passed=False)
def save():status.write_text(json.dumps(report,indent=2)+'\n')
save()
try:
 deadline=time.monotonic()+2400
 while not (analysis/'closure-review.json').exists():
  if time.monotonic()>deadline:raise TimeoutError('boundary collection not completed')
  time.sleep(10)
 spec=importlib.util.spec_from_file_location('review',ROOT/'experiments/lsu-b-validation-v2/review.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);contract=json.loads(m.CONTRACT.read_text());physical=m.review_physical(analysis,'B',contract);assert physical['passed'];period=physical['smallest_tested_passing_period_ps'];assert period!=10000
 report.update(state='measuring-full27',physical_review=physical,period_ps=period);save();out=BASE/f'measurement-{period}ps-v1';command=['python3','scripts/measure_cpu_experiment.py','--experiment','experiments/lsu-b-v1/manifest.json','--build-summary','build/experiments/lsu-b-v1/build-clean-v1/summary.json','--out',str(out),'--period-ps',str(period)];log=BASE/f'measurement-{period}ps-v1-controller.log'
 with log.open('x') as stream:result=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
 report.update(command=command,returncode=result.returncode,log_sha256=sha(log),measurement=str(out.relative_to(ROOT)));assert result.returncode==0 and json.loads((out/'summary.json').read_text())['passed'];report.update(state='finished',passed=True,measurement_summary_sha256=sha(out/'summary.json'))
except Exception as error:report.update(state='blocked',error=repr(error))
finally:report['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save();print(json.dumps(report,indent=2),flush=True)
