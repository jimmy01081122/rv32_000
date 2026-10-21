import json,datetime
from pathlib import Path
root=Path('/workspace/rv32_000');out=root/'build/experiments/lsu-b-v1';s=json.loads((out/'physical-pipeline.json').read_text());p=root/s['active_attempt'];r=json.loads((p/'run.json').read_text());lines=(p/'make.log').read_text(errors='replace').splitlines();m=json.loads((out/'resource-samples.jsonl').read_text().splitlines()[-1]);d={'utc':datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S'),'stage':p.name,'state':r.get('job_state'),'pipeline_complete':s.get('complete'),'error':s.get('error'),'last':lines[-1][-180:] if lines else '', 'freeGiB':round(m['free_disk_bytes']/2**30,3)}
if s.get('commands'):d['controller']=Path(s['commands'][-1]['driver_log']).name;d['controller_rc']=s['commands'][-1].get('returncode')
if s.get('commands'):
 args=s['commands'][-1]['command']
 if 'scripts/analyze_baseline_physical.py' in args:
  label=args[args.index('--label')+1];q=p/label/'run.json'
  if q.exists():d['collected_corners']=[x['corner'] for x in json.loads(q.read_text()).get('records',[])]
if s.get('complete'):d['boundary_ps']=s['smallest_tested_passing_period_ps'];d['common_qualified']=s['common_10000ps_qualified']
post=out/'completion-pipeline.json'
if post.exists():
 c=json.loads(post.read_text());d['post_complete']=c.get('complete');d['post_error']=c.get('error')
 if c.get('period_ps'):
  d['period_ps']=c['period_ps'];q=out/f"measurement-{c['period_ps']}ps-v1/summary.json"
  if q.exists():
   measure=json.loads(q.read_text());d['fastest_records']=len(measure['records']);d['fastest_pass']=measure.get('passed')
print(json.dumps(d))
