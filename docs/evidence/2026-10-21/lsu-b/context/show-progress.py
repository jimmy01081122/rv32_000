import datetime,json
from pathlib import Path
root=Path('/workspace/rv32_000');out=root/'build/experiments/lsu-b-v1'
print(datetime.datetime.now(datetime.timezone.utc).isoformat())
p=out/'physical-pipeline.json'
if p.exists():
 j=json.loads(p.read_text());attempt=root/j['active_attempt'] if j.get('active_attempt') else None
 print('Physical:',attempt.name if attempt else None,'complete:',j.get('complete'),'error:',j.get('error'))
 if attempt:
  state=json.loads((attempt/'run.json').read_text());print('Worker:',state.get('job_state'),'rc:',state.get('returncode'))
  q=attempt/'make.log'
  if q.exists():print('Native:',[s[-160:] for s in q.read_text(errors='replace').splitlines()[-3:]])
 commands=j.get('commands',[])
 if commands:
  c=commands[-1];args=c['command'];print('Controller last command:',Path(c['driver_log']).name,'rc:',c.get('returncode'))
  if 'scripts/analyze_baseline_physical.py' in args and c.get('returncode') is None:
   label=args[args.index('--label')+1];q=attempt/label/'run.json'
   if q.exists():
    collection=json.loads(q.read_text());print('Corner collection:',label,'finished:',[(r['corner'],r['returncode']) for r in collection.get('records',[])])
 if j.get('complete'):print('Boundary:',j['smallest_tested_passing_period_ps'],'common10000 qualified:',j['common_10000ps_qualified'])
else:
 p=out/'measurement-10000ps-v1/summary.json'
 if p.exists():
  j=json.loads(p.read_text());print('Common full27:',len(j['records']),j['passed'])
 p=out/('advance-to-physical-relaunch-v2.log' if (out/'advance-to-physical-relaunch-v2.log').exists() else 'advance-to-physical.log')
 if p.exists():print('Transition:',p.read_text()[-200:])
p=out/'resource-samples.jsonl'
if p.exists():
 r=json.loads(p.read_text().splitlines()[-1]);print('Resource:',r['utc'],'freeGiB:',round(r['free_disk_bytes']/2**30,3),'load:',[round(v,2) for v in r['load_average']],'availableRAMGiB:',round(r['memory_kib']['MemAvailable']/2**20,3))
