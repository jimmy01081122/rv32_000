#!/usr/bin/env python3
"""Actual LSU handoff timing/ownership checks against frozen RTL and candidate."""
import argparse
import json
from pathlib import Path
import subprocess
from baseline_contract import ROOT, sha
from qualify_fp_balanced import run

BASELINE = '58a4159da0372b3286758be1e6c1b50f9f28cc27'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    out=args.out.resolve()
    if not out.is_relative_to(ROOT/'build') or out.exists():
        parser.error('choose a fresh directory under build/')
    out.mkdir(parents=True)
    commits={'baseline':BASELINE,'A':'bf6702c6f4238aaf5f290356f3d0e0279f688f1e',
             'B':'89be789d66e5eb1caddb7dcbeaa443b696eefb67'}
    variants={}
    for name,commit in commits.items():
        directory=out/(name+'-rtl');directory.mkdir()
        path=directory/'rv32_ooo_lsu.sv'
        path.write_bytes(subprocess.check_output(['git','show',commit+':rtl/lsu/rv32_ooo_lsu.sv']))
        variants[name]=path
    original=variants['baseline']
    variants['AB']=ROOT/'rtl/lsu/rv32_ooo_lsu.sv'
    version=subprocess.check_output(['verilator','--version'],text=True).strip()
    if not version.startswith('Verilator 4.038 '):parser.error('pinned Verilator 4.038 required')
    sources=['rtl/pkg/rv32_ooo_params.sv','rtl/pkg/rv32_ooo_types.sv',
             'verification/unit/lsu_marking_top.sv','verification/unit/test_lsu_ab.cpp',
             'rtl/lsu/rv32_ooo_lsu.sv','scripts/check_lsu_ab.py']
    report={'scope':'83 pin-driven cases per actual baseline/A/B/AB RTL plus three negative timing controls; not CPU benchmark speedup',
            'reference_commits':commits,'variant_lsu_sha256':{n:sha(p) for n,p in variants.items()},
            'verilator_version':version,'source_sha256':{p:sha(ROOT/p) for p in sources},
            'builds':[],'records':[],'passed':False}
    summary=out/'summary.json'
    def save():summary.write_text(json.dumps(report,indent=2)+'\n')
    save()
    for name,lsu in variants.items():
        directory=out/name
        cmd=['verilator','--cc','--exe','--assert','-Wall','-Wno-UNUSED',
             '-Wno-STMTDLY','-Wno-PINCONNECTEMPTY','--top-module','lsu_marking_top',
             '--Mdir',str(directory),'-o','lsu_unit','-CFLAGS','-O2',
             'rtl/pkg/rv32_ooo_params.sv','rtl/pkg/rv32_ooo_types.sv',str(lsu),
             'verification/unit/lsu_marking_top.sv',str(ROOT/'verification/unit/test_lsu_ab.cpp')]
        generation=run(cmd,out/(name+'-verilate.log'),120)
        record={'rtl':name,'generation':generation};report['builds'].append(record);save()
        if generation['returncode']:raise SystemExit(1)
        record['compile']=run(['make','-C',str(directory),'-f','Vlsu_marking_top.mk','-j2'],out/(name+'-build.log'),180)
        save()
        if record['compile']['returncode']:raise SystemExit(1)
        binary=directory/'lsu_unit';record['binary_sha256']=sha(binary)
        overlap=int(name in ('A','AB'));marking=int(name in ('B','AB'))
        modes=[(name,overlap,marking,False)]
        if name!='AB':modes.append((name+'-reject-AB',1,1,True))
        for label,expect_a,expect_b,negative in modes:
            trace=out/(label+'.csv');log=out/(label+'.log')
            execution=run([str(binary),str(expect_a),str(expect_b),str(trace)],log,30)
            text=log.read_text()
            expected_failure=('head-store same-cycle availability differs' if name=='A'
                              else 'buffer-consume request availability differs')
            passed=(execution['returncode']==1 and expected_failure in text) if negative else (
                execution['returncode']==0 and text.count('PASS ')==84 and
                'ALL 83 LSU AB CASES PASS' in text)
            # 83 case PASS lines plus the final ALL ... PASS line.
            row={'name':label,'negative_control':negative,'execution':execution,
                 'trace_sha256':sha(trace),'passed':passed}
            report['records'].append(row);save();print(label,passed,flush=True)
    report['input_identities_unchanged']=all(sha(ROOT/p)==h for p,h in report['source_sha256'].items())
    report['passed']=len(report['records'])==7 and all(r['passed'] for r in report['records']) and report['input_identities_unchanged']
    save();raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__':main()
