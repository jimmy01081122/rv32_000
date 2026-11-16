#!/usr/bin/env python3
"""Relink a read-only observer to frozen models; replay three diagnostic cases."""
import argparse, concurrent.futures, datetime, gzip, hashlib, json, shutil, subprocess, sys
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').exists())
HERE=Path(__file__).resolve().parent
EXPERIMENTS={'AB':'lsu-ab-v1','ARB':'lsu-load-arb-v1'}
CASES=[('fp32','pid'),('fp32','fft'),('embench','statemate')]
def require(ok,msg):
    if not ok:raise ValueError(msg)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def archived():
    p=ROOT/'docs/evidence/2026-11-16/lsu-arbitration-functional/inventory.json'
    return {r['path']:r['sha256'] for r in json.loads(p.read_text())['records']}
def build(out,variant):
    out.mkdir();model=ROOT/'build/experiments'/EXPERIMENTS[variant]/'build-v1/sim-normal'
    inc=ROOT/'build/baseline-setup/verilator-source/include'
    source=(ROOT/'sim/tb/sim_main.cpp').read_text()
    edits={
        '#include "core_roi_profile.h"':'#include "core_roi_profile.h"\n#include "arb_observer.h"',
        '    std::string core_profile_file;':'    std::string core_profile_file;\n    std::string arb_observer_file;',
        '        } else if (arg.rfind("+profile-core-roi=", 0) == 0) {':'        } else if (arg.rfind("+observe-arb-raw=", 0) == 0) {\n            config.arb_observer_file = arg.substr(arg.find(\'=\') + 1);\n            config.profile_fp_roi = true;\n        } else if (arg.rfind("+profile-core-roi=", 0) == 0) {',
        '    CoreRoi::Profile core_roi;':'    CoreRoi::Profile core_roi;\n    ArbObserve::Profile arb_observer(config.arb_observer_file);',
        '        if (core_profile_out.is_open() && fp_roi.active) core_roi.sample(CoreRoi::read(*top));':'        if (core_profile_out.is_open() && fp_roi.active) core_roi.sample(CoreRoi::read(*top));\n        arb_observer.sample(*top, fp_roi.active);',
        '        if (core_profile_out.is_open()) core_roi.finish_cycle(retire_valid, commit_pc, commit_insn);':'        if (core_profile_out.is_open()) core_roi.finish_cycle(retire_valid, commit_pc, commit_insn);\n        arb_observer.finish(retire_valid, commit_pc, commit_insn);',
    }
    for old,new in edits.items():
        require(source.count(old)==1,'ambiguous harness edit');source=source.replace(old,new)
    save(out/'harness-replacements.json',edits);(out/'sim_main.cpp').write_text(source)
    objects=[out/'sim_main.o',*[model/n for n in ['sim_mem.o','verilated.o','verilated_vcd_c.o','Vrv32_ooo_core__ALL.a']]]
    inputs=[Path(__file__),HERE/'arb_observer.h',ROOT/'sim/tb/sim_main.cpp',*objects[1:],model/'Vrv32_ooo_core.h',*inc.glob('*.h'),*(ROOT/'sim/tb').glob('*.h')]
    identities={str(p):sha(p) for p in inputs};archive=archived()
    for p in [*objects[1:],model/'Vrv32_ooo_core.h',model/'rv32_ooo_sim']:
        require(sha(p)==archive[str(p.relative_to(ROOT))],'frozen model differs: '+str(p))
    command=['g++','-std=c++14','-O2','-DVM_TRACE=1',f'-DOBSERVER_ARB={int(variant=="ARB")}',*[f'-I{p}' for p in [inc,inc/'vltstd',model,ROOT/'sim/tb',HERE]],'-c',str(out/'sim_main.cpp'),'-o',str(objects[0])]
    link=['g++',*map(str,objects),'-pthread','-o',str(out/'observer')]
    record=dict(variant=variant,compiler=subprocess.check_output(['g++','--version'],text=True),compile_command=command,link_command=link,inputs_sha256=identities,sim_main_sha256=sha(out/'sim_main.cpp'),passed=False)
    save(out/'build.json',record)
    with (out/'build.log').open('w') as log:
        subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run(link,stdout=log,stderr=subprocess.STDOUT,check=True)
    require(all(sha(p)==h for p,h in identities.items()),'build inputs changed')
    record.update(passed=True,simulator_sha256=sha(out/'observer'));save(out/'build.json',record)
    print(variant,'build PASS',flush=True)
def measure(out,variant):
    exe=out/'observer';b=json.loads((out/'build.json').read_text())
    require(b['passed'] and sha(exe)==b['simulator_sha256'],'unreviewed observer')
    base=ROOT/'build/experiments'/EXPERIMENTS[variant]/'measurement-10000ps-v1'
    summary=json.loads((base/'summary.json').read_text());archive=archived();records=[]
    require(sha(base/'summary.json')==archive[str((base/'summary.json').relative_to(ROOT))],'reference summary changed')
    for family,name in CASES:
        ref=base/family/name;case=out/name;case.mkdir()
        row=next(r for r in summary['records'] if (r['family'],r['name'])==(family,name))
        refs={str(p):sha(p) for p in ref.iterdir() if p.is_file()}
        require(all(h==archive[str(Path(p).relative_to(ROOT))] for p,h in refs.items()),'reference changed')
        result=dict(family=family,name=name,reference_sha256=refs,modes={},passed=False)
        for mode in ['off','on']:
            run=case/mode;run.mkdir()
            command=[str(exe),f'+elf={ref}/input.elf','+max-cycles=100000000','+core-period-ps=10000','+imem-response-ps=10000','+imem-interval-ps=10000','+dmem-response-ps=10000',f'+profile-core-roi={run}/profile.json',f'+memory-audit={run}/memory.json']
            raw=run/'cycles.bin'
            if mode=='on':command.append(f'+observe-arb-raw={raw}')
            with (run/'dut.log').open('w') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
            require(r.returncode==0,f'failed {variant}/{name}/{mode}: {run}/dut.log')
            checks={n:(run/n).read_bytes()==(ref/n).read_bytes() for n in ['profile.json','memory.json']}
            oldelf=next(x[5:] for x in row['execution']['command'] if x.startswith('+elf='))
            def normalized(path,elf):
                txt=path.read_text();line='  ELF binary     : '+elf+'\n'
                require(txt.count(line)==1,'unexpected ELF line');return txt.replace(line,'  ELF binary     : <validated frozen ELF>\n',1)
            checks['stdout_equal_after_validated_elf_path']=normalized(run/'dut.log',str(ref/'input.elf'))==normalized(ref/'dut.log',oldelf)
            rec=dict(command=command,returncode=r.returncode,reference_checks=checks)
            if mode=='on':
                require(raw.stat().st_size==json.loads((run/'profile.json').read_text())['cycles']*88*4,'raw length differs from ROI')
                rec['raw_bytes']=raw.stat().st_size;rec['raw_sha256']=sha(raw)
                with raw.open('rb') as src,gzip.GzipFile(filename=str(raw)+'.gz',mode='wb',compresslevel=1,mtime=0) as dst:shutil.copyfileobj(src,dst)
                h=hashlib.sha256();size=0
                with gzip.open(str(raw)+'.gz','rb') as src:
                    for block in iter(lambda:src.read(1048576),b''):h.update(block);size+=len(block)
                require(h.hexdigest()==rec['raw_sha256'] and size==rec['raw_bytes'],'compressed stream differs')
                raw.unlink() # Only redundant temporary raw; compressed copy verified above.
            rec['outputs_sha256']={p.name:sha(p) for p in run.iterdir()};result['modes'][mode]=rec
            save(case/'comparison.json',result);require(all(checks.values()),'observer changed execution')
            print(variant,name,mode,'reference PASS',flush=True)
        require((case/'on/dut.log').read_bytes()==(case/'off/dut.log').read_bytes(),'observer on/off logs differ')
        result['passed']=True;save(case/'comparison.json',result);records.append(result)
    require(all(sha(p)==h for p,h in b['inputs_sha256'].items()),'build inputs changed during run')
    result=dict(passed=True,variant=variant,records=records);save(out/'summary.json',result);return result
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--phase',choices=['build','run'],required=True);a=ap.parse_args();out=a.output.resolve()
    if a.phase=='build':
        require(not out.exists(),'fresh output required');out.mkdir(parents=True)
        for v in EXPERIMENTS:build(out/v,v)
    else:
        state=dict(scope='Three diagnostic cases; frozen RTL and memory 10000 ps; no new family score or PPA',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),controller_sha256=sha(Path(__file__)),passed=False)
        save(out/'summary.json',state)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            tasks={pool.submit(measure,out/v,v):v for v in EXPERIMENTS}
            state['variants']={tasks[f]:f.result() for f in concurrent.futures.as_completed(tasks)}
        state.update(passed=True,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());save(out/'summary.json',state)
if __name__=='__main__':main()
