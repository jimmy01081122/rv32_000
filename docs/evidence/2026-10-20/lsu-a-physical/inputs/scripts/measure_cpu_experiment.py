#!/usr/bin/env python3
"""Complete frozen 27-workload candidate measurement with fixed memory ps."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
from baseline_contract import ROOT,sha
from experiment_contract import load_experiment
from build_experiment_sim import state
from measure_post_lsu_baseline import check_result
from qualify_fp_balanced import run


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--experiment',type=Path,required=True)
    p.add_argument('--build-summary',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--period-ps',type=int,required=True)
    args=p.parse_args();experiment,baseline=load_experiment(args.experiment)
    if args.period_ps<=0:p.error('positive core period required')
    out=args.out.resolve()
    if not out.is_relative_to(ROOT/'build') or out.exists():p.error('choose fresh output under build/')
    start=state()
    if start['status']:p.error('clean committed source required')
    build=json.loads(args.build_summary.read_text())
    if (not build['passed'] or build['experiment_manifest_sha256']!=sha(args.experiment)
            or build['source_sha256']!={**experiment['candidate_rtl_files_sha256'],**experiment['simulation_inputs_sha256']}):
        p.error('candidate build lacks matching successful source proof')
    sim=ROOT/build['executables']['normal']['path']
    if sha(sim)!=build['executables']['normal']['sha256']:p.error('candidate executable changed')
    reference=ROOT/baseline['measurement']['formal_evidence']
    reference_summary=reference/'summary.json'
    if sha(reference_summary)!=baseline['measurement']['formal_summary_sha256']:p.error('baseline results changed')
    reference_records={(r['family'],r['name']):r for r in json.loads(reference_summary.read_text())['records']}
    out.mkdir(parents=True)
    report={'scope':'functional/cycle measurement; system-time/area qualification requires matching independent physical review',
            'experiment_id':experiment['experiment_id'],'experiment_manifest_sha256':sha(args.experiment),
            'build_summary_sha256':sha(args.build_summary),'baseline_summary_sha256':sha(reference_summary),
            'wrapper_sha256':sha(Path(__file__)),'result_checker_sha256':sha(ROOT/'scripts/measure_post_lsu_baseline.py'),
            'start':start,'started_utc':datetime.now(timezone.utc).isoformat(),
            'core_period_ps':args.period_ps,'memory_ps':10000,'simulator_sha256':sha(sim),
            'physical_qualification_pending':True,'records':[],'passed':False}
    summary=out/'summary.json'
    def save():summary.write_text(json.dumps(report,indent=2)+'\n')
    save()
    for row in baseline['workloads']:
        directory=out/row['family']/row['name'];directory.mkdir(parents=True)
        source=ROOT/row['source_elf']
        if sha(source)!=row['elf_sha256']:raise SystemExit('frozen input ELF changed: '+row['name'])
        elf=directory/'input.elf';shutil.copyfile(source,elf)
        audit=directory/'memory.json';profile=directory/'profile.json';log=directory/'dut.log'
        command=[str(sim),f'+elf={elf}','+max-cycles=100000000',f'+core-period-ps={args.period_ps}',
                 '+imem-response-ps=10000','+imem-interval-ps=10000','+dmem-response-ps=10000',
                 f'+memory-audit={audit}',f'+profile-core-roi={profile}']
        execution=run(command,log,600);record={'family':row['family'],'name':row['name'],
                                            'elf_sha256':sha(elf),'execution':execution,'passed':False}
        if execution['returncode']==0 and audit.exists() and profile.exists():
            counters=json.loads(profile.read_text())
            check=check_result(row,log.read_text(),json.loads(audit.read_text()),args.period_ps,10000,elf,counters,
                               require_reference_cycles=False)
            reference_profile=reference/row['family']/row['name']/'profile.json'
            if sha(reference_profile)!=reference_records[row['family'],row['name']]['profile_sha256']:
                raise SystemExit('frozen baseline profile changed: '+row['name'])
            original=json.loads(reference_profile.read_text())
            if counters['retired_classes']!=original['retired_classes']:
                check['problems'].append('retired instruction work differs from frozen baseline')
            record.update(check,profile_sha256=sha(profile),memory_audit_sha256=sha(audit),
                          passed=not check['problems'])
        report['records'].append(record);save();print(row['family'],row['name'],record['passed'],record.get('cycles'),flush=True)
    report.update(end=state(),finished_utc=datetime.now(timezone.utc).isoformat())
    report['passed']=(len(report['records'])==27 and all(r['passed'] for r in report['records'])
                      and report['start']==report['end'] and sha(sim)==report['simulator_sha256']
                      and sha(args.experiment)==report['experiment_manifest_sha256'])
    save();raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__':main()
