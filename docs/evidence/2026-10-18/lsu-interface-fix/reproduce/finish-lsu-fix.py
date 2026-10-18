from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,subprocess,time
out=Path('build/qualification/lsu-fix-run');p=out/'summary.json';d=json.loads(p.read_text())
def capture(cmd):return subprocess.check_output(cmd,text=True).strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert len(d['steps'])==9 and all(s['returncode']==0 for s in d['steps'])
assert d['start']=={'commit':capture(['git','rev-parse','HEAD']),'status':capture(['git','status','--porcelain'])}
cmd=['python3','scripts/test_lsu_candidates.py'];log=out/'9-scripts-test_lsu_candidates.py.log';start=time.monotonic()
with log.open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=60)
d['steps'].append({'command':cmd,'returncode':r.returncode,'log':str(log),'log_sha256':sha(log),'seconds':time.monotonic()-start})
d['orchestrator_recovery']={'reason':'The runner tried to use a script path as a log filename for its final step. All prior nine commands completed successfully. The filename was sanitized and the remaining command run on the same unchanged clean source. No workload failures were retried.','interrupted_runner_log':'build/lsu-fix-qualification.log'}
d.update(end={'commit':capture(['git','rev-parse','HEAD']),'status':capture(['git','status','--porcelain'])},finished_utc=datetime.now(timezone.utc).isoformat())
d['simulators']={str(p):sha(p) for p in (Path('build/sim/rv32_ooo_sim'),Path('build/sim-assert/rv32_ooo_sim'))}
d['passed']=all(s['returncode']==0 for s in d['steps']) and d['start']==d['end']
p.write_text(json.dumps(d,indent=2)+'\n');print('qualification',d['passed']);raise SystemExit(0 if d['passed'] else 1)
