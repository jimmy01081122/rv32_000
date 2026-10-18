from datetime import datetime, timezone
import hashlib,json,subprocess,time
from pathlib import Path
root=Path.cwd();out=Path('build/qualification/lsu-fix-run');out.mkdir(exist_ok=True)
def capture(cmd):return subprocess.check_output(cmd,text=True).strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def state():return {'commit':capture(['git','rev-parse','HEAD']),'status':capture(['git','status','--porcelain'])}
report={'scope':'LSU interface correctness qualification, no optimization or physical signoff', 'started_utc':datetime.now(timezone.utc).isoformat(),'start':state(),'steps':[]}
assert report['start']['status']=='',report['start']
report['images']={i:capture(['docker','image','inspect','--format={{.Id}}',i]) for i in ('rv32ooo-sim:g1','rv32ooo-fp:p1')}
report['source_sha256']={str(p):sha(p) for p in sorted([*Path('rtl').rglob('*.sv'),*Path('sim/tb').glob('*cpp'),*Path('sim/tb').glob('*.h'),Path('scripts/build_sim.sh'),Path('scripts/check_lsu_interface.py'),Path('software/interface/lsu_fault.S'),Path('Makefile')])}
commands=[['make',target,'JOBS=4'] for target in ('lint','check-lsu-interface','test','diff-test','check-fma-finite','qualify-fp-balanced-dut','qualify-embench-fp-dut','summarize-embench-fp-dut')]
commands += [['python3','-m','unittest','discover','-s','scripts','-p','test_fp*.py'],['python3','scripts/test_lsu_candidates.py']]
for i,cmd in enumerate(commands):
 log=out/(str(i)+'-'+cmd[1].replace('/','-')+'.log');start=time.monotonic();print('RUN',cmd,flush=True)
 with log.open('w') as stream:result=subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT,timeout=3600)
 report['steps'].append({'command':cmd,'returncode':result.returncode,'log':str(log),'log_sha256':sha(log),'seconds':time.monotonic()-start})
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
 if result.returncode:break
report.update(end=state(),finished_utc=datetime.now(timezone.utc).isoformat())
report['simulators']={str(p):sha(p) for p in (Path('build/sim/rv32_ooo_sim'),Path('build/sim-assert/rv32_ooo_sim'))}
report['passed']=len(report['steps'])==len(commands) and all(s['returncode']==0 for s in report['steps']) and report['start']==report['end']
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
raise SystemExit(0 if report['passed'] else 1)
