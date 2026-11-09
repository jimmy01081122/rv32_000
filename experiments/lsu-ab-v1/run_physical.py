#!/usr/bin/env python3
"""Run isolated A+B through the exact accepted GRT, hold40 and ready-guard policies."""
import argparse,datetime,hashlib,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'experiments/optimization-135-v1'))
from checkpoint import atomic_json,checkpoint
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BASE=ROOT/'build/experiments/lsu-ab-v1'
REL=Path('results/asap7/rv32_post_lsu_v1/base')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,msg):
    if not ok:raise ValueError(msg)
def load(name):
    p=ROOT/'experiments/lsu-b-validation-v2'/name
    spec=importlib.util.spec_from_file_location(name.split('.')[0],p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def check(policy):
    require(ROOT==Path('/workspace'),'native /workspace mount required')
    require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT),'clean tracked source required')
    require(subprocess.check_output(['git','-C','/orfs-source','rev-parse','HEAD'],text=True).strip()==policy['physical']['orfs_commit'],'wrong ORFS commit')
    require(not subprocess.check_output(['git','-C','/orfs-source','status','--porcelain']),'dirty ORFS')
    for k,h in policy['unchanged_rtl'].items():require(sha(ROOT/k)==h,'current reference RTL changed: '+k)
    for k,h in policy['native_flow_sources_sha256'].items():require(sha(ROOT/k)==h,'native construction source changed: '+k)
    for k,h in policy['study_sources_sha256'].items():require(sha(ROOT/k)==h,'study controller changed: '+k)
    for row in policy['variants'].values():require(sha(ROOT/row['netlist'])==row['netlist_sha256'],'wrong linked netlist')
    require(sha(ROOT/policy['shared_link_manifest']['path'])==policy['shared_link_manifest']['sha256'],'wrong FPU link')
    subprocess.run(['sha256sum','--strict','--quiet','-c','/workspace/docs/evidence/2026-10-18/post-lsu-baseline-preparation/environment/physical-tool-platform-sha256.txt'],check=True)
def main():
    global BASE
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--label',choices=['v1'],required=True);args=ap.parse_args()
    BASE=BASE/'native'
    durable=ROOT/'build/experiments/lsu-ab-v1/checkpoints'
    require(durable.is_dir() and (durable/'host-visible-marker.json').is_file(),'explicit durable host mount/marker required')
    require(BASE.stat().st_dev!=durable.stat().st_dev,'scratch and durable checkpoint mounts must be separate')
    require(shutil.disk_usage(durable).free>=768*1024**2,'need 768 MiB durable checkpoint capacity')
    grt_policy=HERE/'contract-grt.json';eco_policy=HERE/'contract-hold40.json';guard_policy=HERE/'contract-guard.json'
    policies=[json.loads(p.read_text()) for p in [grt_policy,eco_policy,guard_policy]]
    for d in policies:check(d)
    BASE.mkdir(parents=True,exist_ok=True)
    require(shutil.disk_usage(BASE).free>=3*1024**3,'need at least 3 GiB available on the actual experiment output filesystem')
    paths=[BASE/'physical-AB-v1',BASE/'physical-AB-v2',BASE/'physical-AB-v4'];require(not any(p.exists() for p in paths),'preserve existing attempts')
    tracked=[Path(__file__),HERE/'guard_ab.py',ROOT/'experiments/optimization-135-v1/checkpoint.py',grt_policy,eco_policy,guard_policy];report=dict(scope='AB same-flow construction; independent corners/measurement still required',attempt=args.label,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),inputs={str(p):sha(p) for p in tracked},stages=[],checkpoints=[],complete=False);summary=BASE/'physical-controller.json';save(summary,report);atomic_json(durable/'physical-controller.json',report)
    p=paths[0];p.mkdir();state=dict(variant='AB',contract_sha256=sha(grt_policy),stages=[],complete=False);save(p/'pipeline.json',state)
    physical=load('physical.py');physical.CONTRACT=grt_policy;print('START AB GRT',flush=True);physical.run_stage(p/'grt','grt','AB',policies[0]);state.update(stages=['grt'],complete=True);save(p/'pipeline.json',state);report['stages'].append('grt');report['checkpoints'].append(checkpoint(p,durable));save(summary,report);atomic_json(durable/'physical-controller.json',report)
    check(policies[1]);p=paths[1];p.mkdir();(p/'grt').symlink_to('../physical-AB-v1/grt',target_is_directory=True);state=dict(variant='AB',contract_sha256=sha(eco_policy),stages=['grt-reused'],complete=False);save(p/'pipeline.json',state)
    repair=load('repair.py');repair.CONTRACT=eco_policy;print('START AB HOLD40',flush=True);repair.run_stage(p/'eco','eco','AB',policies[1],paths[0]/'grt');state.update(stages=['grt-reused','eco'],complete=True);save(p/'pipeline.json',state);report['stages'].append('eco');report['checkpoints'].append(checkpoint(p,durable));save(summary,report);atomic_json(durable/'physical-controller.json',report)
    incoming=p/'eco';bound=policies[2];bound['variants']['AB']['incoming_physical']=dict(directory=str(incoming.relative_to(ROOT)),report_sha256=sha(incoming/'run.json'),odb_sha256=sha(incoming/REL/'5_1_grt.odb'),sdc_sha256=sha(incoming/REL/'5_1_grt.sdc'));bound['guard_template_sha256']=sha(guard_policy);contract=BASE/'AB-guard-bound-contract.json';require(not contract.exists(),'fresh bound guard contract required');save(contract,bound);check(bound)
    shutil.copyfile(contract,durable/contract.name)
    command=['python3',str(HERE/'guard_ab.py'),'--variant','AB','--contract',str(contract),'--output',str(paths[2])];report['guard_command']=command;save(summary,report);atomic_json(durable/'physical-controller.json',report);print('START AB READY GUARD',flush=True);subprocess.run(command,check=True);report['stages'].append('guard');report['checkpoints'].append(checkpoint(paths[2],durable))
    require(all(sha(Path(p))==h for p,h in report['inputs'].items()),'pipeline source inputs changed')
    report.update(complete=True,input_identities_unchanged=True,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),bound_guard_contract_sha256=sha(contract));save(summary,report);atomic_json(durable/'physical-controller.json',report);print('AB CONSTRUCTION COMPLETE; ALL THREE STAGES DURABLE',flush=True)
if __name__=='__main__':main()
