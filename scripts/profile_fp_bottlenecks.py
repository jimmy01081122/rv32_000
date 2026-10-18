#!/usr/bin/env python3
"""Explain FIR/BiCG contraction with paired architectural and cycle observations."""
import argparse
import json
from pathlib import Path
import re
import subprocess

from compare_fp_contraction import compare
from qualify_fp_balanced import ROOT, BASE, digest, run, validate


def check_profile(profile, record, case, output):
    errors = []
    numeric = validate(case, output)
    text = output.read_text()
    count = re.search(r'^FP ROI cycle_reads=(\d+) retired=(\d+)', text, re.MULTILINE)
    partition, classes = profile['cycle_partition'], profile['retired_classes']
    if not numeric['passed'] or numeric['checksum'] != record['dut_numeric']['checksum']:
        errors.append('numerical output mismatch')
    if numeric['roi_cycles'] != record['dut_numeric']['roi_cycles'] or profile['cycles'] != numeric['roi_cycles']:
        errors.append('CSR ROI cycles / observed commit-window cycles disagree')
    if sum(partition.values()) != profile['cycles']:
        errors.append('cycle partition is incomplete')
    if not count or int(count[1]) != 2 or int(count[2]) != sum(classes.values()):
        errors.append('retired class sum / ROI markers disagree')
    if partition.get('retired_body') != sum(classes.values()) or partition.get('retired_marker') != 1:
        errors.append('retirement partition / marker boundaries disagree')
    if profile['trace_mismatches'] or profile['layout_mismatches']:
        errors.append('pre-edge decode / commit or packed-layout consistency failed')
    if sum(profile['store_ack_wait_phases'].values()) != partition.get('store_ack_wait', 0):
        errors.append('store wait phases are incomplete')
    if sum(profile['load_head_wait_phases'].values()) != sum(partition.get(k, 0) for k in ('head_wait_fp_load', 'head_wait_int_load')):
        errors.append('load wait phases are incomplete')
    return numeric, errors


def summarize(off, fast):
    delta = lambda a, b: {k: b.get(k, 0) - a.get(k, 0) for k in sorted(a.keys() | b.keys())}
    a, b = off['profile'], fast['profile']
    removed = sum(a['retired_classes'].values()) - sum(b['retired_classes'].values())
    saved = a['cycles'] - b['cycles']
    parts = delta(a['cycle_partition'], b['cycle_partition'])
    extra_holes = sum(v for k, v in parts.items() if k not in ('retired_body', 'retired_marker'))
    assert removed == saved + extra_holes
    return {'retired_removed': removed, 'cycles_saved': saved, 'additional_no_retire_cycles': extra_holes,
            'instruction_delta_fast_minus_off': delta(a['retired_classes'], b['retired_classes']),
            'cycle_partition_delta_fast_minus_off': parts,
            'store_wait_delta_fast_minus_off': delta(a['store_ack_wait_phases'], b['store_ack_wait_phases']),
            'load_wait_delta_fast_minus_off': delta(a['load_head_wait_phases'], b['load_head_wait_phases'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comparison-dir', type=Path, default=BASE / 'fma-comparison')
    parser.add_argument('--out-dir', type=Path, default=BASE / 'fma-bottleneck')
    parser.add_argument('--baseline-simulator', type=Path, help='Optional pre-observer binary for explicit invariance replay')
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if not out.is_relative_to(ROOT):
        parser.error('--out-dir must be within the repository')
    out.mkdir(parents=True, exist_ok=True)
    destination = out / 'summary.json'
    destination.unlink(missing_ok=True)
    reports = {mode: json.loads((args.comparison_dir / mode / 'summary.json').read_text()) for mode in ('off', 'fast')}
    paired = compare(reports['off'], reports['fast'])
    if not paired['all_pairs_valid']:
        raise SystemExit(f'Invalid source comparison: {paired["problems"]}')
    simulator = ROOT / 'build/sim/rv32_ooo_sim'
    if any(v['simulator_sha256'] != digest(simulator) for v in reports.values()):
        raise SystemExit('Re-run compare-fp-contraction with the current observer-capable simulator')
    report = {'scope': 'Read-only FIR/BiCG instruction and cycle diagnosis, no RTL optimization or PPA score',
              'repository_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'working_tree_clean': not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip(),
              'simulator_sha256': digest(simulator),
              'rtl_sha256': {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT / 'rtl').rglob('*.sv'))},
              'comparison_sha256': {mode: digest(args.comparison_dir / mode / 'summary.json') for mode in ('off', 'fast')},
              'source_sha256': {p: digest(ROOT / p) for p in ('scripts/profile_fp_bottlenecks.py', 'sim/tb/core_roi_profile.h', 'sim/tb/sim_main.cpp', 'rtl/pkg/rv32_ooo_types.sv')},
              'memory_model': {'ram_bytes': 1048576, 'dmem_latency_cycles': 1, 'random_extra_delay_cycles': 0},
              'records': [], 'results': {}, 'all_passed': False}
    for name in ('fir', 'bicg'):
        per_mode = {}
        for mode in ('off', 'fast'):
            row = next(v for v in reports[mode]['records'] if v['name'] == name)
            source = args.comparison_dir / mode / name
            elf = source / 'rv32.elf'
            if digest(elf) != row['elf_sha256']:
                raise SystemExit(f'{name}/{mode}: ELF changed after paired qualification')
            directory = out / name / mode
            directory.mkdir(parents=True, exist_ok=True)
            profile_path = directory / 'core-profile.json'
            profile_path.unlink(missing_ok=True)
            item = {'name': name, 'mode': mode, 'elf_sha256': digest(elf), 'fixture_sha256': digest(source / 'fixture.json')}
            item['observed'] = run([str(simulator), f'+elf={elf}', '+max-cycles=25000000',
                                    f'+profile-core-roi={profile_path}'], directory / 'observed.log', 180)
            item['problems'] = []
            if item['observed']['returncode'] == 0 and profile_path.exists():
                item['profile'] = json.loads(profile_path.read_text())
                item['profile_sha256'] = digest(profile_path)
                item['numeric'], errors = check_profile(item['profile'], row, json.loads((source / 'fixture.json').read_text()), directory / 'observed.log')
                item['problems'].extend(errors)
                item['observer_stdout_matches_qualified_run'] = digest(directory / 'observed.log') == row['dut']['log_sha256']
                if not item['observer_stdout_matches_qualified_run']:
                    item['problems'].append('observer changed qualified stdout')
            else:
                item['problems'].append('observed run failed or profile missing')
            # Same current binary / ELF, all ROI observers disabled.
            item['unobserved'] = run([str(simulator), f'+elf={elf}', '+max-cycles=25000000'], directory / 'unobserved.log', 180)
            plain = (directory / 'unobserved.log').read_text()
            observed = (directory / 'observed.log').read_text()
            remove_profile = lambda text: re.sub(r'^FP ROI .*\n', '', text, flags=re.MULTILINE)
            item['unobserved_stdout_matches'] = remove_profile(observed) == plain
            if item['unobserved']['returncode'] or not item['unobserved_stdout_matches']:
                item['problems'].append('observer invariance replay failed')
            if args.baseline_simulator:
                item['baseline_simulator_sha256'] = digest(args.baseline_simulator)
                item['baseline'] = run([str(args.baseline_simulator.resolve()), f'+elf={elf}', '+max-cycles=25000000'], directory / 'baseline.log', 180)
                item['baseline_stdout_matches'] = (directory / 'baseline.log').read_text() == plain
                if item['baseline']['returncode'] or not item['baseline_stdout_matches']:
                    item['problems'].append('pre-observer model invariance replay failed')
            item['passed'] = not item['problems']
            report['records'].append(item); per_mode[mode] = item
            destination.write_text(json.dumps(report, indent=2) + '\n')
            print(name, mode, 'PASS' if item['passed'] else item['problems'], flush=True)
        if all(v['passed'] for v in per_mode.values()):
            report['results'][name] = summarize(per_mode['off'], per_mode['fast'])
    report['all_passed'] = len(report['records']) == 4 and all(v['passed'] for v in report['records'])
    report['working_tree_clean_at_end'] = not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()
    destination.write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['all_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
