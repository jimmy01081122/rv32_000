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
    (out/'baseline-rtl').mkdir()
    original=out/'baseline-rtl/rv32_ooo_lsu.sv'
    original.write_bytes(subprocess.check_output(['git','show',BASELINE+':rtl/lsu/rv32_ooo_lsu.sv']))
    version=subprocess.check_output(['verilator','--version'],text=True).strip()
    if not version.startswith('Verilator 4.038 '):parser.error('pinned Verilator 4.038 required')
    sources=['rtl/pkg/rv32_ooo_params.sv','rtl/pkg/rv32_ooo_types.sv',
             'verification/unit/lsu_overlap_top.sv','verification/unit/test_lsu_overlap.cpp',
             'rtl/lsu/rv32_ooo_lsu.sv','scripts/check_lsu_overlap.py']
    report={'scope':'20 pin-driven LSU cases per RTL plus original-RTL negative timing control; not CPU benchmark speedup',
            'baseline_commit':BASELINE,'baseline_lsu_sha256':sha(original),
            'verilator_version':version,'source_sha256':{p:sha(ROOT/p) for p in sources},
            'builds':[],'records':[],'passed':False}
    summary=out/'summary.json'
    def save():summary.write_text(json.dumps(report,indent=2)+'\n')
    save()
    for name,lsu in [('baseline',original),('candidate',ROOT/'rtl/lsu/rv32_ooo_lsu.sv')]:
        directory=out/name
        cmd=['verilator','--cc','--exe','--assert','-Wall','-Wno-UNUSED',
             '-Wno-STMTDLY','-Wno-PINCONNECTEMPTY','--top-module','lsu_overlap_top',
             '--Mdir',str(directory),'-o','lsu_unit','-CFLAGS','-O2',
             'rtl/pkg/rv32_ooo_params.sv','rtl/pkg/rv32_ooo_types.sv',str(lsu),
             'verification/unit/lsu_overlap_top.sv',str(ROOT/'verification/unit/test_lsu_overlap.cpp')]
        generation=run(cmd,out/(name+'-verilate.log'),120)
        record={'rtl':name,'generation':generation};report['builds'].append(record);save()
        if generation['returncode']:raise SystemExit(1)
        record['compile']=run(['make','-C',str(directory),'-f','Vlsu_overlap_top.mk','-j2'],out/(name+'-build.log'),180)
        save()
        if record['compile']['returncode']:raise SystemExit(1)
        binary=directory/'lsu_unit';record['binary_sha256']=sha(binary)
        modes=[('baseline',0,False),('baseline-reject-A-timing',1,True)] if name=='baseline' else [('candidate',1,False)]
        for label,mode,negative in modes:
            trace=out/(label+'.csv');log=out/(label+'.log')
            execution=run([str(binary),str(mode),str(trace)],log,30)
            text=log.read_text()
            passed=(execution['returncode']!=0 and 'buffer-consume request availability differs' in text) if negative else (
                execution['returncode']==0 and text.count('PASS ')==21 and
                'ALL 20 LSU HANDOFF CASES PASS' in text)
            # 20 case PASS lines plus the final ALL ... PASS line.
            row={'name':label,'negative_control':negative,'execution':execution,
                 'trace_sha256':sha(trace),'passed':passed}
            report['records'].append(row);save();print(label,passed,flush=True)
    report['input_identities_unchanged']=all(sha(ROOT/p)==h for p,h in report['source_sha256'].items())
    report['passed']=len(report['records'])==3 and all(r['passed'] for r in report['records']) and report['input_identities_unchanged']
    save();raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__':main()
