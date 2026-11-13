#!/usr/bin/env python3
"""Pin-driven parent/candidate arbitration checks with actual RTL negative controls."""
import argparse,json,subprocess
from pathlib import Path
from baseline_contract import ROOT,sha
from qualify_fp_balanced import run

PARENT='49122fb9b37292c9a2c2dc4b4b70226909304293'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if not out.is_relative_to(ROOT/'build') or out.exists():parser.error('fresh build directory required')
    version=subprocess.check_output(['verilator','--version'],text=True).strip()
    if not version.startswith('Verilator 4.038 '):parser.error('pinned Verilator required')
    out.mkdir(parents=True);source=ROOT/'rtl/lsu/rv32_ooo_lsu.sv';rtl=source.read_text()
    variants={'parent':subprocess.check_output(['git','show',PARENT+':rtl/lsu/rv32_ooo_lsu.sv'],cwd=ROOT).decode(),
              'candidate':rtl}
    mutations={
      'unbounded':('(!sq_has_send || load_request_held || first_head_store)','(!sq_has_send || load_request_held || first_head_store || sq_has_send)'),
      'no-hold':('(!sq_has_send || load_request_held || first_head_store)','(!sq_has_send || first_head_store)'),
    }
    for name,(old,new) in mutations.items():
        assert rtl.count(old)==1
        variants[name]=rtl.replace(old,new)
    sources=['rtl/pkg/rv32_ooo_params.sv','rtl/pkg/rv32_ooo_types.sv','rtl/lsu/rv32_ooo_lsu.sv',
             'verification/unit/lsu_marking_top.sv','verification/unit/test_lsu_ab.cpp',
             'verification/unit/test_lsu_arbitration.cpp','scripts/check_lsu_arbitration.py']
    report=dict(passed=False,parent_commit=PARENT,verilator_version=version,
                scope='140 pin-driven cases per parent/candidate and actual RTL negative controls; no benchmark/physical claim',
                source_sha256={n:sha(ROOT/n) for n in sources},builds=[],records=[])
    def save():(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    for name,text in variants.items():
        path=out/(name+'-rtl')/'rv32_ooo_lsu.sv';path.parent.mkdir();path.write_text(text);directory=out/name
        command=['verilator','--cc','--exe','--assert','-Wall','-Wno-UNUSED','-Wno-STMTDLY',
                 '-Wno-PINCONNECTEMPTY','--top-module','lsu_marking_top','--Mdir',str(directory),
                 '-o','lsu_unit','-CFLAGS','-O2','rtl/pkg/rv32_ooo_params.sv','rtl/pkg/rv32_ooo_types.sv',
                 str(path),'verification/unit/lsu_marking_top.sv',str(ROOT/'verification/unit/test_lsu_arbitration.cpp')]
        generated=run(command,out/(name+'-verilate.log'),120)
        build=dict(variant=name,rtl_sha256=sha(path),generation=generated);report['builds'].append(build);save()
        if generated['returncode']:raise SystemExit(1)
        build['compile']=run(['make','-C',str(directory),'-f','Vlsu_marking_top.mk','-j2'],out/(name+'-build.log'),180);save()
        if build['compile']['returncode']:raise SystemExit(1)
        binary=directory/'lsu_unit';build['binary_sha256']=sha(binary)
        modes=[(name,name!='parent',name not in ['parent','candidate'])]
        if name=='parent':modes.append(('parent-reject-candidate',True,True))
        for label,expect,negative in modes:
            log=out/(label+'.log');trace=out/(label+'.csv')
            execution=run([str(binary),str(int(expect)),str(trace)],log,60);result=log.read_text()
            failure={'parent-reject-candidate':'first eligible head arbitration differs',
                     'unbounded':'store arbitration or AGU hold wrong',
                     'no-hold':'offered request changed under backpressure'}
            passed=(execution['returncode']!=0 and failure[label] in result) if negative else (
                execution['returncode']==0 and result.count('PASS ')==140 and 'ALL 140 LSU ARBITRATION CASES PASS' in result)
            report['records'].append(dict(name=label,negative_control=negative,execution=execution,
                                          trace_sha256=sha(trace),passed=passed));save();print(label,passed,flush=True)
            if not passed:raise SystemExit(1)
    report['input_identities_unchanged']=all(sha(ROOT/n)==h for n,h in report['source_sha256'].items())
    report['passed']=len(report['records'])==5 and all(r['passed'] for r in report['records']) and report['input_identities_unchanged'];save()
    raise SystemExit(0 if report['passed'] else 1)

if __name__=='__main__':main()
