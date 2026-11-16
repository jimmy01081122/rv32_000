#!/usr/bin/env python3
"""Real ROB occupancy + LSU pin tests, with actual parent and RTL mutants."""
import argparse,json,subprocess
from pathlib import Path
from baseline_contract import ROOT,sha
from qualify_fp_balanced import run
PARENT='3715907cbe65f342a1db1dbfaeef1e2b9f5f15b6'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();out=a.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'build'):ap.error('fresh output under build required')
    version=subprocess.check_output(['verilator','--version'],text=True).strip()
    if not version.startswith('Verilator 4.038 '):ap.error('pinned Verilator required')
    out.mkdir(parents=True)
    adapter=out/'lsu_marking_top.sv'
    adapter.write_bytes((ROOT/'verification/unit/lsu_rob_room_top.sv').read_bytes())
    sources=['rtl/pkg/rv32_ooo_params.sv','rtl/pkg/rv32_ooo_types.sv','rtl/lsu/rv32_ooo_lsu.sv','rtl/rob/rv32_ooo_rob.sv','rtl/core/rv32_ooo_core.sv',
        'verification/unit/lsu_rob_room_top.sv','verification/unit/test_lsu_rob_room.cpp','verification/unit/test_lsu_arbitration.cpp','verification/unit/test_lsu_ab.cpp','scripts/check_lsu_rob_room.py']
    lsu=(ROOT/sources[2]).read_text();rob=(ROOT/sources[3]).read_text()
    def replace(s,old,new):
        assert s.count(old)==1;return s.replace(old,new)
    variants={
        'parent':(subprocess.check_output(['git','show',PARENT+':'+sources[2]],cwd=ROOT,text=True),rob),
        'candidate':(lsu,rob),
        'threshold-15':(lsu,replace(rob,"5'(ROB_ENTRIES - 2)","5'(ROB_ENTRIES - 1)")),
        'threshold-13':(lsu,replace(rob,"5'(ROB_ENTRIES - 2)","5'(ROB_ENTRIES - 3)")),
        'pressure-revokes-held':(replace(lsu,'!sq_has_send || load_request_held ||','!sq_has_send || (load_request_held && load_bypass_room) ||'),rob),
        'unbounded':(replace(lsu,'!sq_has_send || load_request_held ||','!sq_has_send || sq_has_send || load_request_held ||'),rob),
        'no-hold':(replace(lsu,'!sq_has_send || load_request_held ||','!sq_has_send ||'),rob),
    }
    report=dict(passed=False,parent_commit=PARENT,verilator_version=version,scope='344 actual-ROB/LSU pin cases per parent/candidate; six negative controls; no score/PPA',source_sha256={n:sha(ROOT/n) for n in sources},builds=[],records=[])
    def save():(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    for name,(ls,rb) in variants.items():
        src=out/(name+'-rtl');src.mkdir();(src/'rv32_ooo_lsu.sv').write_text(ls);(src/'rv32_ooo_rob.sv').write_text(rb);directory=out/name
        command=['verilator','--cc','--exe','--assert','-Wall','-Wno-UNUSED','-Wno-STMTDLY','-Wno-PINCONNECTEMPTY','--top-module','lsu_marking_top','--Mdir',str(directory),'-o','lsu_unit','-CFLAGS','-O2']
        if name!='parent':command+=['+define+ROOM_CANDIDATE']
        command+=['rtl/pkg/rv32_ooo_params.sv','rtl/pkg/rv32_ooo_types.sv',str(src/'rv32_ooo_lsu.sv'),str(src/'rv32_ooo_rob.sv'),str(adapter),str(ROOT/'verification/unit/test_lsu_rob_room.cpp')]
        generation=run(command,out/(name+'-verilate.log'),120)
        build=dict(variant=name,lsu_sha256=sha(src/'rv32_ooo_lsu.sv'),rob_sha256=sha(src/'rv32_ooo_rob.sv'),generation=generation);report['builds'].append(build);save()
        if generation['returncode']:raise SystemExit(1)
        build['compile']=run(['make','-C',str(directory),'-f','Vlsu_marking_top.mk','-j2'],out/(name+'-build.log'),180);save()
        if build['compile']['returncode']:raise SystemExit(1)
        exe=directory/'lsu_unit';build['binary_sha256']=sha(exe)
        modes=[(name,name!='parent',name not in ['parent','candidate'])]
        if name=='parent':modes.append(('parent-reject-room',True,True))
        for label,expect,negative in modes:
            log=out/(label+'.log');trace=out/(label+'.csv');execution=run([str(exe),str(int(expect)),str(trace)],log,60);text=log.read_text()
            signatures={'parent-reject-room':'ROB pressure decision differs','threshold-15':'ROB threshold differs','threshold-13':'ROB threshold differs','pressure-revokes-held':'held load revoked when ROB filled','unbounded':'store arbitration or AGU hold wrong','no-hold':'offered request changed under backpressure'}
            passed=(execution['returncode']!=0 and signatures[label] in text) if negative else (execution['returncode']==0 and text.count('PASS ')==344 and 'ALL 344 LSU ROB ROOM CASES PASS' in text)
            report['records'].append(dict(name=label,negative_control=negative,execution=execution,trace_sha256=sha(trace),passed=passed));save();print(label,passed,flush=True)
            if not passed:raise SystemExit(1)
    report['input_identities_unchanged']=all(sha(ROOT/n)==h for n,h in report['source_sha256'].items())
    report['passed']=len(report['records'])==8 and all(r['passed'] for r in report['records']) and report['input_identities_unchanged'];save()
    raise SystemExit(0 if report['passed'] else 1)
if __name__=='__main__':main()
