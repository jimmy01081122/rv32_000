#!/usr/bin/env python3
"""Portable pinned ORFS global-route run; no slack-derived frequency claims."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ORFS_SHA = '8359fde81991e6118b15b8a93fcde606b577794d'
IMAGE = 'rv32ooo-orfs:8359fde-flat'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--period-ps', type=int, default=5500, help='exploration constraint, not achieved timing')
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--container', help='reuse a running pinned-image container with the documented mounts')
    parser.add_argument('--label', default='', help='unique attempt suffix; existing logs are never overwritten')
    parser.add_argument('--resume-reason', help='resume a failed attempt with identical hashed build inputs; retain the prior log')
    args = parser.parse_args()
    if args.period_ps <= 2200 or args.jobs < 1:
        parser.error('period must exceed frozen 1100ps input + output budgets; jobs positive')
    if args.label and not re.fullmatch(r'[a-zA-Z0-9_-]+', args.label):
        parser.error('label may contain letters, digits, underscore and hyphen only')
    source = ROOT / 'build/baseline-setup/ORFS'
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != ORFS_SHA or subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain']):
        parser.exit(1, 'ORFS checkout must be the pinned clean revision\n')
    suffix = f'-{args.label}' if args.label else ''
    directory = ROOT / f'build/baselines/ap5b-post-lsu-v1/physical-{args.period_ps}ps{suffix}'
    previous = None
    if args.resume_reason:
        if not (directory/'run.json').exists():parser.error('resume requires an existing failed attempt')
        previous = json.loads((directory/'run.json').read_text())
        if not previous.get('returncode'):parser.error('only a finished failed attempt may be resumed')
    elif (directory/'run.json').exists():
        parser.exit(1, 'attempt already exists; choose a fresh --label\n')
    directory.mkdir(parents=True, exist_ok=True)
    sdc = directory / 'constraint.sdc'
    # Absolute I/O/uncertainty/load remain unchanged across period trials.
    constraint = f'''create_clock -name core_clk -period {args.period_ps} [get_ports clk]
set_clock_uncertainty -setup 50 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_transition 20 [all_inputs]
set_input_delay -max 1100 -clock core_clk [all_inputs -no_clocks]
set_input_delay -min 0 -clock core_clk [all_inputs -no_clocks]
set_output_delay -max 1100 -clock core_clk [all_outputs]
set_output_delay -min 0 -clock core_clk [all_outputs]
set_load 2 [all_outputs]
group_path -name in2reg -from [all_inputs -no_clocks] -to [all_registers]
group_path -name reg2out -from [all_registers] -to [all_outputs]
group_path -name reg2reg -from [all_registers] -to [all_registers]
group_path -name in2out -from [all_inputs -no_clocks] -to [all_outputs]
'''
    if not sdc.exists() or sdc.read_text()!=constraint:
        if previous:parser.error('resume constraint differs from the failed attempt')
        sdc.write_text(constraint)
    def guest(path):
        return '/workspace/' + str(path.relative_to(ROOT))
    expected_image = subprocess.check_output(['docker','image','inspect',IMAGE,'--format','{{.Id}}'], text=True).strip()
    prefix = ['docker', 'run', '--rm', '--user', '1000:1000', '-v', f'{ROOT}:/workspace',
           '-v', f'{source}:/orfs-source:ro', '-w', '/workspace', '--entrypoint', '/bin/bash',
           IMAGE]
    if args.container:
        actual = json.loads(subprocess.check_output(['docker','inspect',args.container],text=True))[0]
        mounts = {m['Destination']: m['Source'] for m in actual['Mounts']}
        if (not actual['State']['Running'] or actual['Image'] != expected_image
                or mounts.get('/workspace') != str(ROOT) or mounts.get('/orfs-source') != str(source)):
            parser.exit(1, 'container image, state or source mounts do not match the pinned setup\n')
        prefix = ['docker','exec','--user','1000:1000','-w','/workspace',args.container,'/bin/bash']
    cmd = prefix + ['-c', 'exec make -f /orfs-source/flow/Makefile "$@"', 'baseline-orfs',
           'FLOW_HOME=/orfs-source/flow', 'PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7',
           'PLATFORMS_DIR=/OpenROAD-flow-scripts/flow/platforms',
           'OPENROAD_EXE=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',
           'YOSYS_EXE=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys',
           'RV32_ROOT=/workspace', f'RV32_SDC={guest(sdc)}', f'WORK_HOME={guest(directory)}',
           'DESIGN_CONFIG=/workspace/physical/asap7/baseline/config.mk',
           f'NUM_CORES={args.jobs}', 'grt']
    report = {'scope': 'global-route research baseline exploration, not detailed-route signoff',
              'period_ps': args.period_ps, 'orfs_commit': commit, 'command': cmd,
              'sdc_sha256': sha(sdc), 'lowered_rtl_sha256': sha(ROOT/'build/baseline-setup/rtl_lowered.v'),
              'rtl_files_sha256': {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT/'rtl').rglob('*.sv'))},
              'config_sha256': sha(ROOT/'physical/asap7/baseline/config.mk'), 'passed': False}
    report['local_image_id'] = expected_image
    report['process_lowering_sha256'] = sha(ROOT/'physical/asap7/baseline/lower_processes.tcl')
    report['source_commit'] = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    report['source_status'] = subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).splitlines()
    if previous:
        for field in ('period_ps','orfs_commit','command','sdc_sha256','lowered_rtl_sha256',
                      'rtl_files_sha256','config_sha256','local_image_id','process_lowering_sha256'):
            if previous[field]!=report[field]:parser.error('resume input changed: '+field)
        history=previous.pop('previous_attempts',[])
        prior_log=directory/f'make-attempt{len(history)+1}.log'
        if prior_log.exists():parser.error('prior log already exists; refusing overwrite')
        (directory/'make.log').rename(prior_log)
        previous.update(log=str(prior_log.relative_to(ROOT)),resume_reason=args.resume_reason)
        history.append(previous);report['previous_attempts']=history
    summary = directory/'run.json';summary.write_text(json.dumps(report,indent=2)+'\n')
    with (directory/'make.log').open('w') as log:
        result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    report.update(returncode=result.returncode, log_sha256=sha(directory/'make.log'))
    # Closure requires separate corner/path/area/constraint checks, never just rc=0.
    report['flow_completed'] = result.returncode == 0
    summary.write_text(json.dumps(report,indent=2)+'\n')
    print('global-route command returncode',result.returncode,flush=True)
    raise SystemExit(result.returncode)

if __name__ == '__main__':
    main()
