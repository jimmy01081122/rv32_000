#!/usr/bin/env python3
"""Recheck six DIV observers, all 27 case selection profiles and hardware controls."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').exists())
BASE=ROOT/'build/experiments/divider-diagnosis-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def require(ok,msg):
    if not ok:raise ValueError(msg)
def local(s):
    p=Path(s)
    if not p.is_absolute():return ROOT/p
    return p if p.is_relative_to(ROOT) else ROOT/p.relative_to('/workspace')
def isdiv(insn):
    i=int(insn,16);return i&127==0x33 and i>>25==1 and ((i>>12)&7)>=4
def review():
    accepted=ROOT/'build/experiments/lsu-b-validation-v2/final-common-clock-review.json'
    require(sha(accepted)=='c133e45ff7ad30f1ad049a13a45f4c66b3c8a6d37e6cad85daa8aee397de0ea0','accepted B review changed')
    reference=ROOT/'build/experiments/lsu-b-validation-v2/measurement-10000ps-v1'
    require(sha(reference/'summary.json')==read(accepted)['measurement']['measurement_summary_sha256'],'B measurement changed')
    ref=read(reference/'summary.json');selection={};profile_hashes={}
    require(ref['passed'] and len(ref['records'])==27,'complete reference required')
    for r in ref['records']:
        path=reference/r['family']/r['name']/'profile.json';require(sha(path)==r['profile_sha256'],'reference profile changed')
        profile=read(path);pcs=[x for x in profile['pcs'] if isdiv(x['insn']) and x['retired']]
        profile_hashes[r['name']]=sha(path)
        if pcs:selection[r['name']]=dict(pcs=pcs,cycles=profile['cycles'],family=r['family'])
    require(set(selection)=={'ud','wikisort','st','cubic','nbody','nettle-aes'},'DIV-active selection differs')
    run=BASE/'observer-v1';state=read(run/'summary.json');summary=read(run/'B/summary.json');build=read(run/'B/build.json')
    require(state['passed'] and summary['passed'] and build['passed'] and len(summary['records'])==6,'incomplete observer study')
    require(summary['original_measurement_summary_sha256']==sha(reference/'summary.json'),'observer reference mismatch')
    require('11.4.0' in build['compiler'],'observer compiler differs')
    for p,h in {**state['inputs_sha256'],**build['inputs_sha256']}.items():require(sha(local(p))==h,'observer input changed: '+p)
    require(sha(run/'B/observer')==build['simulator_sha256'],'observer executable changed')
    require(sha(ROOT/'build/experiments/lsu-b-v1/build-clean-v1/sim-normal/rv32_ooo_sim')==ref['simulator_sha256'],'original scored model changed')
    rows=[]
    for row in summary['records']:
        name=row['name'];case=run/'B'/name;old=reference/'embench'/name
        require(row['passed'] and row==read(case/'comparison.json'),'observer case record differs')
        require(sha(old/'input.elf')==row['elf_sha256'] and sha(old/'profile.json')==row['reference_profile_sha256'] and
                sha(old/'dut.log')==row['reference_log_sha256'],'retained case evidence changed')
        for mode in ['off','on']:
            data=row['modes'][mode];require(data['returncode']==0 and all(data['reference_checks'].values()),'failed observer identity')
            for p,h in data['outputs_sha256'].items():require(sha(case/mode/p)==h,'observer raw output changed')
            for file in ['profile.json','memory.json']:require(sha(case/mode/file)==sha(old/file),'observer execution differs')
        require(sha(case/'off/dut.log')==sha(case/'on/dut.log'),'observer on/off log differs')
        obs=read(case/'on/observer.json');c=obs['counts'];hist=obs['histograms'];issues=c['accepted_issues']
        require(obs['cycles']==selection[name]['cycles'],'observer ROI differs')
        cats={k.removeprefix('operands_'):v for k,v in c.items() if k.startswith('operands_')}
        require(sum(cats.values())==issues==sum(hist['pc_issues'].values()),'operand/PC denominator differs')
        require(issues==c.get('issued_in_roi_completed_in_roi',0)+c.get('cancelled_by_flush',0)+c.get('censored_at_roi_end',0),
                'issue lifecycle mismatch')
        require(sum(hist['issue_to_grant'].values())==c.get('issued_in_roi_completed_in_roi',0),'latency pairs mismatch')
        opportunities=sum(cats.get(k,0) for k in ['abs_divisor_one','abs_dividend_less','remaining_power_two'])
        z=hist.get('non_special_abs_dividend_leading_zeros',{})
        rows.append(dict(name=name,roi_cycles=obs['cycles'],accepted_issues=issues,
           retired_div_rem=sum(p['retired'] for p in selection[name]['pcs']),
           div_rem_head_wait=sum(p['head_wait'] for p in selection[name]['pcs']),
           cancelled_by_flush=c.get('cancelled_by_flush',0),censored_at_roi_end=c.get('censored_at_roi_end',0),
           operand_categories=cats,new_early_result_operand_fraction=opportunities/issues,
           non_special_mean_abs_dividend_leading_zeros=sum(int(k)*v for k,v in z.items())/sum(z.values()),
           issue_to_first_valid=hist['issue_to_first_valid'],issue_to_grant=hist['issue_to_grant'],
           completion_blocked_cycles=c.get('completion_blocked_cycles',0),request_not_ready_cycles=c.get('request_not_ready_cycles',0),
           observer_sha256=sha(case/'on/observer.json'),per_pc_retired=selection[name]['pcs']))
    control=BASE/'controls-v2';d=read(control/'summary.json')
    require(d['passed'] and d['observer_sha256']==build['simulator_sha256'] and d['original_sha256']==ref['simulator_sha256'],
            'control executable identity differs')
    require(d['source_sha256']==sha(BASE/'source/check_controls.py') and d['elf_sha256']==sha(control/'input.elf') and
            d['vectors_sha256']==sha(control/'vectors.json'),'control source or vectors changed')
    for r in d['records']:
        require(r['returncode']==0,'failed hardware control')
        for p,h in r['outputs_sha256'].items():require(sha(control/r['mode']/p)==h,'control raw evidence changed')
    for file in ['profile.json','trace.log']:require(len({sha(control/m/file) for m in ['original','off','on']})==1,'control execution differs')
    require(d['observer']==read(control/'on/observer.json'),'control observer changed')
    require(d['observer']['histograms']['issue_to_first_valid']=={'1':6,'33':42},'48 control latencies changed')
    expected={'abs_dividend_less':20,'abs_divisor_one':4,'existing_overflow':2,'existing_zero':4,'general':12,'remaining_power_two':6}
    require(all(d['observer']['counts']['operands_'+k]==v for k,v in expected.items()),'hardware operand categories differ')
    return dict(passed=True,scope='Read-only retained B diagnosis; accepted issue operand counts can include speculation and are not saved cycles or CPU speedup',
                reviewer_sha256=sha(Path(__file__)),accepted_reference_sha256=sha(accepted),reference_profiles_checked=27,
                reference_profiles_sha256=profile_hashes,observer_case_pairs=6,hardware_control_instructions=48,
                observer_build_sha256=sha(run/'B/build.json'),observer_summary_sha256=sha(run/'B/summary.json'),
                hardware_controls_sha256=sha(control/'summary.json'),records=rows)
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(not a.output.exists(),'fresh review output required');d=review();a.output.write_text(json.dumps(d,indent=2)+'\n')
    print('DIV diagnosis PASS: 27 selection profiles, six on/off pairs, 48 instruction controls')
if __name__=='__main__':main()
