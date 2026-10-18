#!/usr/bin/env python3
"""Portable pinned ORFS global-route run; no slack-derived frequency claims."""
import argparse
import hashlib
import json
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
    args = parser.parse_args()
    if args.period_ps <= 2200 or args.jobs < 1:
        parser.error('period must exceed frozen 1100ps input + output budgets; jobs positive')
    source = ROOT / 'build/baseline-setup/ORFS'
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != ORFS_SHA or subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain']):
        parser.exit(1, 'ORFS checkout must be the pinned clean revision\n')
    directory = ROOT / f'build/baselines/ap5b-post-lsu-v1/physical-{args.period_ps}ps'
    directory.mkdir(parents=True, exist_ok=True)
    sdc = directory / 'constraint.sdc'
    # Absolute I/O/uncertainty/load remain unchanged across period trials.
    sdc.write_text(f'''create_clock -name core_clk -period {args.period_ps} [get_ports clk]
set_clock_uncertainty -setup 50 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_transition 20 [all_inputs]
set_input_delay 1100 -clock core_clk [all_inputs -no_clocks]
set_output_delay 1100 -clock core_clk [all_outputs]
set_load 2 [all_outputs]
group_path -name in2reg -from [all_inputs -no_clocks] -to [all_registers]
group_path -name reg2out -from [all_registers] -to [all_outputs]
group_path -name reg2reg -from [all_registers] -to [all_registers]
group_path -name in2out -from [all_inputs -no_clocks] -to [all_outputs]
''')
    def guest(path):
        return '/workspace/' + str(path.relative_to(ROOT))
    cmd = ['docker', 'run', '--rm', '--user', '1000:1000', '-v', f'{ROOT}:/workspace',
           '-v', f'{source}:/orfs-source:ro', '-w', '/workspace', '--entrypoint', '/bin/bash',
           IMAGE, '-c', 'exec make -f /orfs-source/flow/Makefile "$@"', 'baseline-orfs',
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
