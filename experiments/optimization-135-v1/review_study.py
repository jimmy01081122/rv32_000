#!/usr/bin/env python3
"""Independently check read-only observations against immutable scored records."""
import argparse, json
from pathlib import Path
from analyze_retained import MEASUREMENTS, MODELS, require, sha, retained, paths
def log_payload(p,elf):
    text=p.read_text();line='  ELF binary     : '+str(elf)+'\n'
    require(text.count(line)==1,'ELF path declaration mismatch')
    return text.replace(line,'  ELF binary     : <validated frozen ELF>\n',1)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True)
    for v in ['baseline','A','B']:ap.add_argument('--'+v,type=Path,required=True)
    ap.add_argument('--controls',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    retained(a.repo);paths(a.repo)
    results=[];input_sources={};orig={}
    for v in ['baseline','A','B']:
        run=getattr(a,v);d=json.loads((run/'summary.json').read_text());build=json.loads((run/'build.json').read_text())
        require(d['passed'] and len(d['records'])==9 and build['passed'],'incomplete observer variant')
        require(sha(run/'observer')==build['simulator_sha256'],'observer executable changed')
        for p,h in build['inputs_sha256'].items():require(sha(Path(p))==h,'observer build input changed: '+p)
        input_sources[v]=dict(build_sha256=sha(run/'build.json'),summary_sha256=sha(run/'summary.json'),observer_sha256=sha(run/'observer'))
        base=a.repo/MEASUREMENTS[v];reference=json.loads((base/'summary.json').read_text())
        selected=[r for r in reference['records'] if r['family']=='fp32' or r['name']=='minver']
        require({r['name'] for r in selected}=={r['name'] for r in d['records']},'case set mismatch')
        for r in selected:
            case=run/r['name'];ref=base/r['family']/r['name'];old_elf=next(x[5:] for x in r['execution']['command'] if x.startswith('+elf='))
            for mode in ['off','on']:
                for name,field in [('profile.json','profile_sha256'),('memory.json','memory_audit_sha256')]:
                    require(sha(case/mode/name)==r[field],'observer/reference changed '+name)
                require(log_payload(case/mode/'dut.log',ref/'input.elf')==log_payload(ref/'dut.log',old_elf),'changed numerical/cycle/output log')
            require(sha(case/'on/dut.log')==sha(case/'off/dut.log'),'on/off logs differ')
            obs=json.loads((case/'on/observer.json').read_text());profile=json.loads((ref/'profile.json').read_text());c=obs['counts'];h=obs['histograms']
            require(obs['cycles']==r['cycles'],'wrong ROI length')
            require(c.get('arithmetic_issues',0)==profile['overlapping_events']['heavy_issue'],'issue mismatch')
            live=r['cycles']-c.get('flush_cycles',0)
            require(sum(h['completion_valid_mask'].values())==live,'completion mask histogram missing cycles')
            for unit in ['simple','arithmetic','divsqrt']:
                require(c.get(unit+'_ready_cycles',0)+c.get(unit+'_not_ready_cycles',0)==live,'FU-ready histogram missing cycles')
            require(c.get('blocked_ex0_with_other_unit_ready_iq',0)<=c.get('blocked_ex0_with_ready_iq',0)<=c.get('ex0_blocked',0),'invalid opportunity counts')
            require(c.get('ex0_blocked',0)<=profile['overlapping_events']['fp_ex0_blocked'],'flush filtering mismatch')
            results.append(dict(variant=v,name=r['name'],family=r['family'],cycles=r['cycles'],
                observer_sha256=sha(case/'on/observer.json'),counts=c,histograms=h,
                old_fp_ex0_including_flush=profile['overlapping_events']['fp_ex0_blocked'],
                old_iq_downstream_including_flush=profile['overlapping_events']['fp_iq_ready_downstream_blocked']))
        orig[v]=sha(a.repo/MODELS[v]/'rv32_ooo_sim')
    controls=json.loads((a.controls/'summary.json').read_text());require(controls['passed'],'hardware controls failed')
    require(controls['original_sha256']==orig['B'] and controls['observer_sha256']==input_sources['B']['observer_sha256'],'control executable identity mismatch')
    total=0
    for r in controls['records']:
        case=a.controls/str(r['nops'])
        require(sha(case/'input.elf')==r['elf_sha256'],'control ELF changed')
        for mode in ['original','off','on']:
            require('Exit status    : PASS (0)' in (case/mode/'dut.log').read_text(),'control result failed')
            require(sha(case/mode/'trace.log')==r['trace_sha256'],'control ordered trace changed')
            require(sha(case/mode/'profile.json')==sha(case/'original/profile.json'),'control profile changed')
        require(json.loads((case/'on/observer.json').read_text())==r['observer'],'control observer changed')
        total+=r['observer']['counts'].get('divsqrt_completion_blocked',0)
    require(total>0 and total==controls['divsqrt_completion_blocked_cycles'],'missing actual contention positive control')
    result=dict(scope='Diagnostic observation review, not a fresh complete architectural or performance qualification',
        source_inputs=input_sources,retained_profiles_checked=81,observer_case_pairs=27,observer_executions=54,
        ordered_trace_control_programs=6,control_executions=18,hardware_contention_cycles=total,
        records=results,passed=True,physical_A_status='not started: Docker access unavailable and workspace disk exhausted')
    a.output.write_text(json.dumps(result,indent=2)+'\n');print('PASS: 81 retained profiles, 27 on/off pairs, 6 original/off/on controls')
if __name__=='__main__':main()
