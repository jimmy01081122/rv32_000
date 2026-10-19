#!/usr/bin/env python3
"""Build normal/assertion models with clean-source and input identity proof."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
from baseline_contract import ROOT,sha
from experiment_contract import load_experiment
from qualify_fp_balanced import run


def state():
    return {'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'status':subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--experiment',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--jobs',type=int,default=2)
    args=p.parse_args();experiment,_=load_experiment(args.experiment)
    out=args.out.resolve()
    if not out.is_relative_to(ROOT/'build') or out.exists():p.error('choose fresh build output under build/')
    start=state()
    if start['status']:p.error('clean committed source required')
    version=subprocess.check_output(['verilator','--version'],text=True).strip()
    gcc=subprocess.check_output(['g++','--version'],text=True).splitlines()[0]
    if not version.startswith('Verilator 4.038 ') or '11.4.0' not in gcc:p.error('pinned Verilator/GCC required')
    out.mkdir(parents=True)
    sources={**experiment['candidate_rtl_files_sha256'],**experiment['simulation_inputs_sha256']}
    report={'scope':'candidate generated-model and runtime build provenance','start':start,
            'started_utc':datetime.now(timezone.utc).isoformat(),'experiment_id':experiment['experiment_id'],
            'experiment_manifest_sha256':sha(args.experiment),'wrapper_sha256':sha(Path(__file__)),
            'source_sha256':sources,'verilator_version':version,'gxx_version':gcc,'executables':{},'records':[],'passed':False}
    summary=out/'summary.json'
    def save():summary.write_text(json.dumps(report,indent=2)+'\n')
    save()
    for mode,assertions in [('normal','0'),('assert','1')]:
        directory=out/('sim-'+mode)
        command=['env','SIM_BUILD_DIR='+str(directory.relative_to(ROOT)),
                 'SIM_ASSERTIONS='+assertions,'OBJCACHE=', 'bash','scripts/build_sim.sh',str(args.jobs)]
        record=run(command,out/(mode+'-build.log'),600);report['records'].append(record);save()
        if record['returncode']:raise SystemExit(1)
        binary=directory/'rv32_ooo_sim'
        generated=directory/'Vrv32_ooo_core__verFiles.dat'
        command_line=next(line for line in generated.read_text().splitlines() if line.startswith('C '))
        if (' --assert ' in command_line)!=(assertions=='1'):raise SystemExit('generated assert mode differs')
        report['executables'][mode]={'path':str(binary.relative_to(ROOT)),'sha256':sha(binary),
                                    'verilator_command':command_line,'verFiles_sha256':sha(generated)}
        save();print(mode,'build complete',flush=True)
    report.update(end=state(),finished_utc=datetime.now(timezone.utc).isoformat())
    report['passed']=(report['start']==report['end'] and all(sha(ROOT/n)==h for n,h in sources.items())
                      and sha(args.experiment)==report['experiment_manifest_sha256'])
    save();raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__':main()
