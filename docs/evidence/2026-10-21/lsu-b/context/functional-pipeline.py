import json,subprocess,datetime
from pathlib import Path
p=Path('build/experiments/lsu-b-v1/functional-pipeline.json')
r={'commands':[],'complete':False}
commands=[['python3', 'scripts/check_lsu_marking.py', '--out', 'build/experiments/lsu-b-v1/unit-clean-v1'], ['python3', 'scripts/qualify_cpu_experiment.py', '--experiment', 'experiments/lsu-b-v1/manifest.json', '--build-summary', 'build/experiments/lsu-b-v1/build-clean-v1/summary.json', '--out', 'build/experiments/lsu-b-v1/qualification-clean-v1'], ['python3', 'scripts/measure_cpu_experiment.py', '--experiment', 'experiments/lsu-b-v1/manifest.json', '--build-summary', 'build/experiments/lsu-b-v1/build-clean-v1/summary.json', '--out', 'build/experiments/lsu-b-v1/measurement-10000ps-v1', '--period-ps', '10000']]
for i,command in enumerate(commands):
 log=p.parent/('functional-stage-'+str(i)+'.log')
 row={'command':command,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};r['commands'].append(row);p.write_text(json.dumps(r,indent=2)+'\n')
 with log.open('w') as f: result=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
 row.update(returncode=result.returncode,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());p.write_text(json.dumps(r,indent=2)+'\n')
 if result.returncode:raise SystemExit(result.returncode)
r['complete']=True;p.write_text(json.dumps(r,indent=2)+'\n')
