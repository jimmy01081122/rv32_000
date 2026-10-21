#!/usr/bin/env python3
"""Isolated directed, Spike, fault, memory-model and finite-FMA regression."""
import argparse
import json
from pathlib import Path
from baseline_contract import ROOT,sha
from experiment_contract import load_experiment
from qualify_fp_balanced import run
from build_experiment_sim import state


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--experiment',type=Path,required=True)
    p.add_argument('--build-summary',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();experiment,_=load_experiment(args.experiment)
    out=args.out.resolve()
    if not out.is_relative_to(ROOT/'build') or out.exists():p.error('fresh output under build required')
    start=state()
    if start['status']:p.error('clean source required')
    build=json.loads(args.build_summary.read_text())
    if not build['passed'] or build['experiment_manifest_sha256']!=sha(args.experiment):p.error('matching build proof required')
    normal=ROOT/build['executables']['normal']['path'];assertions=ROOT/build['executables']['assert']['path']
    for name,exe in [('normal',normal),('assert',assertions)]:
        if sha(exe)!=build['executables'][name]['sha256']:p.error('candidate executable changed')
    out.mkdir(parents=True)
    report={'scope':'targeted regression, not complete ISA/F coverage or performance qualification',
            'start':start,'experiment_manifest_sha256':sha(args.experiment),
            'build_summary_sha256':sha(args.build_summary),'records':[],'passed':False}
    summary=out/'summary.json'
    def save():summary.write_text(json.dumps(report,indent=2)+'\n')
    save()
    elfs=sorted((ROOT/'build/tests').glob('*.elf'))
    if len(elfs)!=18:raise SystemExit('expected exact directed corpus of 18 ELFs')
    for elf in elfs:
        result=run([str(normal),f'+elf={elf}','+max-cycles=1000000'],out/(elf.stem+'.log'),60)
        text=(out/(elf.stem+'.log')).read_text()
        report['records'].append({'name':'directed-'+elf.stem,'elf_sha256':sha(elf),'execution':result,
                                  'passed':result['returncode']==0 and 'PASS (0)' in text and 'TRAP encountered' not in text})
        save()
    checks=[('spike',['python3','scripts/run_spike_diff.py','--sim',str(normal),'--out',str(out/'spike'),'--json'],
             out/'spike/diff_results.json','all_passed'),
            ('interface',['python3','scripts/check_lsu_interface.py','--sim',str(assertions),'--out',str(out/'interface')],
             out/'interface/summary.json','passed'),
            ('memory',['python3','scripts/check_memory_time.py','--sim',str(assertions),'--reference-sim',str(normal),'--out',str(out/'memory')],
             out/'memory/summary.json','passed'),
            ('fma',['python3','scripts/check_fma_finite.py','--sim',str(normal),'--out',str(out/'fma')],
             out/'fma/summary.json','all_passed')]
    for name,command,result_path,flag in checks:
        result=run(command,out/(name+'-driver.log'),600)
        data=json.loads(result_path.read_text()) if result_path.exists() else {}
        passed=result['returncode']==0 and data.get(flag) is True
        if name=='spike':passed &= data.get('total')==18 and data.get('passed')==18
        if name=='interface':passed &= len(data.get('records',[]))==48
        if name=='memory':passed &= len(data.get('records',[]))==58
        if name=='fma':passed &= data.get('vector_count')==3400
        report['records'].append({'name':name,'execution':result,'summary_sha256':sha(result_path) if result_path.exists() else None,'passed':passed})
        save();print(name,passed,flush=True)
    report.update(end=state())
    report['passed']=(len(report['records'])==22 and all(r['passed'] for r in report['records'])
                      and report['start']==report['end'] and sha(args.experiment)==report['experiment_manifest_sha256']
                      and all(sha(ROOT/r['path'])==r['sha256'] for r in build['executables'].values()))
    save();raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__':main()
