#!/usr/bin/env python3
"""Relink only the host harness, then compare observer off/on to scored records."""
import argparse, concurrent.futures, datetime, hashlib, json, subprocess
from pathlib import Path
from analyze_retained import MEASUREMENTS, MODELS, require, sha, retained
HERE=Path(__file__).resolve().parent
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def build(root,out,variant):
    model=root/MODELS[variant]; inc=root/'build/baseline-setup/verilator-source/include'
    source=(root/'sim/tb/sim_main.cpp').read_text()
    for old,new in json.loads((HERE/'harness-replacements.json').read_text()).items():
        require(source.count(old)==1,'ambiguous harness edit');source=source.replace(old,new)
    (out/'sim_main.cpp').write_text(source)
    obj=out/'sim_main.o';exe=out/'observer'
    command=['g++','-std=c++14','-O2','-DVM_TRACE=1',*[f'-I{p}' for p in [inc,inc/'vltstd',model,root/'sim/tb',HERE]],'-c',str(out/'sim_main.cpp'),'-o',str(obj)]
    objects=[obj,model/'sim_mem.o',model/'verilated.o',model/'verilated_vcd_c.o',model/'Vrv32_ooo_core__ALL.a']
    link=['g++',*[str(p) for p in objects],'-pthread','-o',str(exe)]
    inputs=[HERE/'fp_observer.h',HERE/'harness-replacements.json',root/'sim/tb/sim_main.cpp',*objects[1:],
            model/'Vrv32_ooo_core.h',*inc.glob('*.h'),*Path(root/'sim/tb').glob('*.h')]
    identities={str(p):sha(p) for p in inputs}
    d=dict(scope='Host harness relink only; original generated RTL model/runtime objects unchanged',
        compiler=subprocess.check_output(['g++','--version'],text=True),compile_command=command,link_command=link,
        inputs_sha256=identities,sim_main_sha256=sha(out/'sim_main.cpp'))
    save(out/'build.json',d)
    with (out/'build.log').open('w') as log:
        subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run(link,stdout=log,stderr=subprocess.STDOUT,check=True)
    require(all(sha(Path(p))==h for p,h in identities.items()),'build inputs changed')
    d.update(simulator_sha256=sha(exe),passed=True);save(out/'build.json',d)
    return exe,identities
def measure(root,out,variant):
    out.mkdir();exe,identities=build(root,out,variant)
    base=root/MEASUREMENTS[variant];summary=json.loads((base/'summary.json').read_text())
    records=[]
    for row in summary['records']:
        if row['family']!='fp32' and row['name']!='minver':continue
        ref=base/row['family']/row['name']; case=out/row['name'];case.mkdir()
        result=dict(family=row['family'],name=row['name'],reference_profile_sha256=row['profile_sha256'],
            reference_log_sha256=row['execution']['log_sha256'],elf_sha256=row['elf_sha256'],modes={})
        for mode in ['off','on']:
            run=case/mode;run.mkdir()
            command=[str(exe),f'+elf={ref}/input.elf','+max-cycles=100000000','+core-period-ps=10000',
                '+imem-response-ps=10000','+imem-interval-ps=10000','+dmem-response-ps=10000',
                f'+profile-core-roi={run}/profile.json',f'+memory-audit={run}/memory.json']
            if mode=='on':command.append(f'+observe-fp={run}/observer.json')
            with (run/'dut.log').open('w') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
            require(r.returncode==0,f'{variant}/{row["name"]}/{mode} failed: {run}/dut.log')
            checks={name:(run/name).read_bytes()==(ref/name).read_bytes() for name in ['profile.json','memory.json']}
            old_elf=next(x[5:] for x in row['execution']['command'] if x.startswith('+elf='))
            def normalized_log(path, elf):
                text=path.read_text(); line='  ELF binary     : '+elf
                require(text.count(line+'\n')==1,'unexpected ELF identity line')
                return text.replace(line, '  ELF binary     : <validated frozen ELF>',1)
            checks['log_equal_after_validated_ELF_path']=normalized_log(run/'dut.log',str(ref/'input.elf'))==normalized_log(ref/'dut.log',old_elf)
            result['modes'][mode]=dict(command=command,returncode=r.returncode,reference_checks=checks,
                outputs_sha256={p.name:sha(p) for p in run.iterdir()})
            save(case/'comparison.json',result)
            require(all(checks.values()),f'observer changed execution: {case}')
        require((case/'on/dut.log').read_bytes()==(case/'off/dut.log').read_bytes(),'observer on/off logs differ')
        obs=json.loads((case/'on/observer.json').read_text());old=json.loads((ref/'profile.json').read_text())
        require(obs['cycles']==old['cycles'],'ROI mismatch')
        require(obs['counts'].get('arithmetic_issues',0)==old['overlapping_events']['heavy_issue'],'issue counter mismatch')
        result['passed']=True;save(case/'comparison.json',result);records.append(result)
        print(variant,row['name'],'on/off/reference PASS',flush=True)
    require(len(records)==9,'incomplete FP-active case set')
    require(all(sha(Path(p))==h for p,h in identities.items()),'observer inputs changed during run')
    d=dict(variant=variant,scope='Nine FP-active frozen workloads only; other 18 Embench cases are covered by retained profile review, no new performance score',
        original_measurement_summary_sha256=sha(base/'summary.json'),records=records,passed=True)
    save(out/'summary.json',d);return d
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--variants',nargs='+',choices=list(MODELS),default=list(MODELS));a=ap.parse_args()
    require(not a.output.exists(),'fresh output required');a.output.mkdir(parents=True)
    retained(a.repo) # includes exact frozen ELFs, profiles and scored simulator identities
    inputs={str(p):sha(p) for p in [Path(__file__),HERE/'fp_observer.h',HERE/'harness-replacements.json',HERE/'analyze_retained.py']}
    state=dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),inputs_sha256=inputs,selected_variants=a.variants,passed=False)
    save(a.output/'summary.json',state)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(measure,a.repo,a.output/v,v):v for v in a.variants}
        state['variants']={futures[f]:f.result() for f in concurrent.futures.as_completed(futures)}
    require(all(sha(Path(p))==h for p,h in inputs.items()),'controller inputs changed')
    state.update(passed=True,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());save(a.output/'summary.json',state)
if __name__=='__main__':main()
