#!/usr/bin/env python3
"""Run the three frozen inputs in a fresh directory inside the pinned runtime."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from run_physical_job import execute, write_json

INPUTS = {
    'baseline': ('build/baseline-setup/rtl_lowered.v',
                 '2cbf3fa60c07b6cf21a81c5317e54b28c873bdee050df43793382ae9956d7382'),
    'A': ('build/experiments/lsu-a-v1/rtl_lowered.v',
          'f57b627d8b84f5cda1222d206f2c786fa328abcb09e368815873d1749860176e'),
    'B': ('build/experiments/lsu-b-v1/rtl_lowered.v',
          '9ce8b80aaad06d4b24345c10f373ed9d9d3ce28aad82b022ae7cedee0ee3b2e6'),
}
FPU_SHA = '769b647361eb5bce78fd58923e646c3da2b47016042bbc69984983d6a17805bb'
PLATFORM_MANIFEST = ROOT / 'docs/evidence/2026-10-18/post-lsu-baseline-preparation/environment/physical-tool-platform-sha256.txt'
SDC = '''create_clock -name core_clk -period 5500 [get_ports clk]
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


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def checked(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--variants', nargs='+', choices=INPUTS, default=['B', 'baseline', 'A'])
    args = parser.parse_args()
    out = args.output.resolve()
    checked(out.is_relative_to(ROOT / 'build'), 'output must be under build/')
    checked(len(args.variants) == len(set(args.variants)), 'duplicate variant')
    checked(not out.exists(), 'fresh output directory required')
    checked(ROOT == Path('/workspace'), 'run inside the documented pinned runtime')
    checked(subprocess.check_output(['git', '-C', '/orfs-source', 'rev-parse', 'HEAD'], text=True).strip()
            == '8359fde81991e6118b15b8a93fcde606b577794d', 'wrong ORFS revision')
    checked(not subprocess.check_output(['git', '-C', '/orfs-source', 'status', '--porcelain']), 'dirty ORFS')
    checked(not subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain']), 'commit flow before measurement')
    subprocess.run(['sha256sum', '--strict', '--quiet', '-c', str(PLATFORM_MANIFEST)], check=True)
    inputs = {}
    for variant, (path, expected) in INPUTS.items():
        p = ROOT / path
        checked(sha(p) == expected, 'changed frozen input: ' + variant)
        matches = re.findall(r'^module rv32_ooo_fp_execute\s*\(.*?^endmodule', p.read_text(), re.M | re.S)
        checked(len(matches) == 1 and hashlib.sha256(matches[0].encode()).hexdigest() == FPU_SHA,
                'changed FPU body: ' + variant)
        inputs[str(p)] = expected
    guards = [Path(__file__), ROOT / 'scripts/run_physical_job.py', PLATFORM_MANIFEST]
    guards += list((ROOT / 'physical/asap7/baseline').glob('*'))
    guards += list((ROOT / 'physical/asap7/fpu-isolated').glob('*'))
    for p in guards:
        if p.is_file():
            inputs[str(p)] = sha(p)
    out.mkdir(parents=True)
    state = dict(scope='FPU mapping isolation; synthesis only, no qualified PPA',
                 source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                 started_utc=datetime.now(timezone.utc).isoformat(), inputs=inputs,
                 jobs=[], complete=False)
    write_json(out / 'pipeline.json', state)
    for variant in args.variants:
        directory = out / variant
        directory.mkdir()
        sdc = directory / 'constraint.sdc'
        sdc.write_text(SDC)
        cmd = ['make', '-f', '/orfs-source/flow/Makefile', 'FLOW_HOME=/orfs-source/flow',
               'PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7',
               'PLATFORMS_DIR=/OpenROAD-flow-scripts/flow/platforms',
               'OPENROAD_EXE=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',
               'YOSYS_EXE=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys',
               'RV32_ROOT=/workspace', 'RV32_SDC=' + str(sdc), 'WORK_HOME=' + str(directory),
               'DESIGN_CONFIG=/workspace/physical/asap7/fpu-isolated/config.mk',
               'VERILOG_FILES=' + str(ROOT / INPUTS[variant][0]), 'NUM_CORES=2',
               'GPL_RANDOM_SEED=', 'CORNER=TC', 'CORNERS=typical', 'REPORT_CLOCK_SKEW=0',
               'OPT_POST_GRT_WNS=0', 'ADDER_MAP_FILE=', 'synth']
        report = directory / 'run.json'
        write_json(report, dict(variant=variant, source_commit=state['source_commit'],
                               command=cmd, mapping_period_ps=5500, keep_module='rv32_ooo_fp_execute',
                               scope=state['scope'], passed=False))
        spec = directory / 'job.json'
        write_json(spec, dict(report=str(report), log=str(directory / 'make.log'),
                              cwd=str(ROOT), command=cmd, inputs={**inputs, str(sdc): sha(sdc)}))
        state['jobs'].append(str(report.relative_to(ROOT)))
        write_json(out / 'pipeline.json', state)
        print('START', variant, flush=True)
        checked(execute(spec) == 0, 'native synthesis failed: ' + variant)
        print('DONE', variant, flush=True)
    subprocess.run(['sha256sum', '--strict', '--quiet', '-c', str(PLATFORM_MANIFEST)], check=True)
    state.update(complete=True, finished_utc=datetime.now(timezone.utc).isoformat())
    write_json(out / 'pipeline.json', state)


if __name__ == '__main__':
    main()
