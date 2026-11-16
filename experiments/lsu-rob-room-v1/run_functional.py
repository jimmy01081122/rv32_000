#!/usr/bin/env python3
"""Sequential clean-source build, qualification, full measurement and review."""
import datetime,json,os,subprocess,sys
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').exists())
sys.path.insert(0,str(ROOT/'scripts'))
from baseline_contract import sha
from build_experiment_sim import state
BASE=ROOT/'build/experiments/lsu-rob-room-v1'
def main():
    receipt=BASE/'functional-pipeline.json'
    if receipt.exists():raise ValueError('preserve previous pipeline')
    unit=json.loads((BASE/'unit-v2/summary.json').read_text())
    if not unit['passed'] or any(sha(ROOT/n)!=h for n,h in unit['source_sha256'].items()):raise ValueError('current unit inputs must pass')
    start=state()
    if start['status']:raise ValueError('clean committed inputs required')
    env=os.environ.copy()
    for key in ['DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:env.pop(key,None)
    docker=['docker','--host=unix:///var/run/docker.sock'];image='rv32ooo-fp:p1'
    image_id=subprocess.check_output(docker+['image','inspect','--format','{{.Id}}',image],env=env,text=True).strip()
    if image_id!='sha256:2140263677b3a378d5cab75a3d0d4fd285ddb38a1a5a1f81f5cf97db024a02d5':raise ValueError('pinned image changed')
    container=docker+['run','--rm','--network','none','--ulimit','core=0','--user',f'{os.getuid()}:{os.getgid()}','--volume',f'{ROOT}:{ROOT}','--workdir',str(ROOT),'--entrypoint','python3',image]
    contract='experiments/lsu-rob-room-v1/manifest.json';build=BASE/'build-v1/summary.json';measurement=BASE/'measurement-10000ps-v1'
    commands=[
      ('build',container+['scripts/build_experiment_sim.py','--experiment',contract,'--out',str(build.parent),'--jobs','2']),
      ('qualification',container+['scripts/qualify_cpu_experiment.py','--experiment',contract,'--build-summary',str(build),'--out',str(BASE/'qualification-v1')]),
      ('measurement',['python3','scripts/measure_cpu_experiment.py','--experiment',contract,'--build-summary',str(build),'--out',str(measurement),'--period-ps','10000']),
      ('review',['python3','experiments/lsu-rob-room-v1/review_measurement.py','--measurement',str(measurement),'--output',str(BASE/'common-clock-review.json')]),
      ('comparison',['python3','experiments/lsu-rob-room-v1/compare_parents.py','--output',str(BASE/'parent-comparison.json')]),
    ]
    now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
    report=dict(complete=False,started_utc=now(),start=start,controller_sha256=sha(Path(__file__)),unit_summary_sha256=sha(BASE/'unit-v2/summary.json'),image_id=image_id,steps=[])
    def save():receipt.write_text(json.dumps(report,indent=2)+'\n')
    for name,command in commands:
        report['active_stage']=name;save();print(now(),name,'START',flush=True);log=BASE/(name+'-driver.log')
        with log.open('w') as f:r=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
        report['steps'].append(dict(name=name,command=command,returncode=r.returncode,log_sha256=sha(log)));save()
        print(now(),name,'exit',r.returncode,flush=True)
        if r.returncode:raise SystemExit(r.returncode)
    report.update(end=state(),active_stage=None,finished_utc=now());report['complete']=report['end']==start and sha(Path(__file__))==report['controller_sha256'];save()
    if not report['complete']:raise SystemExit('source changed during pipeline')
if __name__=='__main__':main()
