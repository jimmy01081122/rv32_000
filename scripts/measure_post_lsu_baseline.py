#!/usr/bin/env python3
"""Measure all frozen workloads with physical-time memory and independent checks."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
from baseline_contract import ROOT,MANIFEST,load,validate,check_rtl,sha,image_end
from qualify_fp_balanced import run,validate as numeric

OUT=ROOT/'build/baselines/ap5b-post-lsu-v1/measurement'
def state():return {'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'status':subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()}
def check_result(row,text,audit,core_ps,memory_ps,elf,profile,*,require_reference_cycles=True):
    problems=[]
    if not audit['fixed_time'] or any(audit[k]!=v for k,v in {
        'core_period_ps':core_ps,'imem_response_ps':memory_ps,
        'imem_interval_ps':memory_ps,'dmem_response_ps':memory_ps}.items()):
        problems.append('memory audit configuration differs from the contract')
    for port in ('imem','dmem'):
        if not 0<audit[port+'_responses']<=audit[port+'_requests']:
            problems.append(port+' transaction audit inconsistent or empty')
    if 'Exit status    : PASS (0)' not in text or 'TRAP encountered' in text:problems.append('program failure/unexpected trap')
    if row['family']=='fp32':
        class Output:
            def read_text(self):return text
        result=numeric(json.loads((ROOT/row['fixture']).read_text()),Output())
        cycles=result.get('roi_cycles')
        if not result.get('passed') or result.get('checksum')!=row['reference_checksum']:problems.append('independent numerical validation failed')
    else:
        result=None;match=re.search(r'Benchmark executed in cycles: (\d+)',text);cycles=int(match[1]) if match else None
    if require_reference_cycles and cycles!=row['reference_cycles']:problems.append('nominal ROI differs from qualified frozen reference')
    if not isinstance(cycles,int) or cycles<=0:problems.append('missing/non-positive ROI cycles')
    for field in ('imem_min_response_ps','dmem_min_response_ps'):
        if audit[field]<memory_ps:problems.append(field+' shorter than fixed memory time')
    for field in ('imem_max_response_ps','dmem_max_response_ps'):
        if audit[field]>=memory_ps+core_ps:problems.append(field+' outside reference sampling bound')
    if not audit['stack_pointer_seen'] or not (image_end(elf)<=audit['minimum_retired_sp']<=0x80100000):problems.append('stack/data overlap or missing stack audit')
    if profile['cycles']!=cycles or profile['trace_mismatches'] or profile['layout_mismatches']:problems.append('ROI observer consistency failed')
    if sum(profile['cycle_partition'].values())!=cycles:problems.append('cycle partition incomplete')
    return {'cycles':cycles,'numeric':result,'static_image_end':image_end(elf),'stack_headroom_bytes':audit['minimum_retired_sp']-image_end(elf),'problems':problems}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--period-ps',type=int,required=True,help='actual checked baseline period, or explicitly labeled preparation timing')
    parser.add_argument('--preparation',action='store_true',help='model qualification only; cannot freeze physical baseline')
    parser.add_argument('--label',default='',help='unique attempt suffix; existing measurements are never overwritten')
    args=parser.parse_args()
    if args.label and not re.fullmatch(r'[a-zA-Z0-9_-]+',args.label):parser.error('invalid attempt label')
    global OUT
    if args.label:OUT=OUT.with_name(OUT.name+'-'+args.label)
    OUT.mkdir(parents=True,exist_ok=True);destination=OUT/'summary.json'
    if destination.exists():parser.exit(1,'measurement already exists; choose a fresh --label\n')
    manifest=load();rows=validate(manifest);check_rtl(manifest);start=state()
    if start['status']:raise SystemExit('baseline measurement requires a clean worktree')
    if args.period_ps<=0:parser.error('positive ps period required')
    if not args.preparation and manifest['physical']['closed_period_ps']!=args.period_ps:parser.error('need checked physical period in manifest')
    sim=ROOT/'build/sim/rv32_ooo_sim';report={'baseline_id':manifest['baseline_id'],'manifest_sha256':sha(MANIFEST),'started_utc':datetime.now(timezone.utc).isoformat(),'start':start,'period_ps':args.period_ps,'memory_ps':args.period_ps,'preparation_only':args.preparation,'simulator_sha256':sha(sim),'records':[],'passed':False}
    destination.write_text(json.dumps(report,indent=2)+'\n')
    for row in rows:
        directory=OUT/row['family']/row['name'];directory.mkdir(parents=True,exist_ok=True)
        source=ROOT/row['source_elf'];elf=directory/'input.elf'
        if not source.is_file() or sha(source)!=row['elf_sha256']:raise SystemExit('missing/changed frozen ELF: '+str(source))
        shutil.copyfile(source,elf);audit_path=directory/'memory.json';profile_path=directory/'profile.json'
        for path in (audit_path,profile_path):path.unlink(missing_ok=True)
        command=[str(sim),f'+elf={elf}','+max-cycles=100000000',f'+core-period-ps={args.period_ps}',f'+imem-response-ps={args.period_ps}',f'+imem-interval-ps={args.period_ps}',f'+dmem-response-ps={args.period_ps}',f'+memory-audit={audit_path}',f'+profile-core-roi={profile_path}']
        record={'family':row['family'],'name':row['name'],'elf_sha256':sha(elf),'execution':run(command,directory/'dut.log',600),'passed':False}
        if record['execution']['returncode']==0 and audit_path.exists() and profile_path.exists():
            audit=json.loads(audit_path.read_text());profile=json.loads(profile_path.read_text());check=check_result(row,(directory/'dut.log').read_text(),audit,args.period_ps,args.period_ps,elf,profile);record.update(check)
            record.update(memory_audit=str(audit_path.relative_to(ROOT)),memory_audit_sha256=sha(audit_path),profile=str(profile_path.relative_to(ROOT)),profile_sha256=sha(profile_path),passed=not check['problems'])
        report['records'].append(record);destination.write_text(json.dumps(report,indent=2)+'\n');print(row['family'],row['name'],record['passed'],record.get('cycles'),flush=True)
    report.update(end=state(),finished_utc=datetime.now(timezone.utc).isoformat())
    report['passed']=len(report['records'])==27 and all(r['passed'] for r in report['records']) and report['start']==report['end'] and sha(sim)==report['simulator_sha256']
    destination.write_text(json.dumps(report,indent=2)+'\n');raise SystemExit(0 if report['passed'] else 1)
if __name__=='__main__':main()
