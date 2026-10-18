#!/usr/bin/env python3
"""Run matched off/fast FP32 diagnostics with identical inputs and hardware."""
import argparse
import hashlib
import json
import math
import re
import struct
from pathlib import Path
import subprocess

from fp_balanced_fixtures import NAMES
from qualify_fp_balanced import ROOT, BASE


def compare(off, fast):
    problems, rows = [], []
    for label, report in (('off', off), ('fast', fast)):
        if (report.get('selected') != list(NAMES) or report.get('passed_count') != 8
                or not report.get('all_passed') or not report.get('run_dut')
                or not report.get('profile_roi') or report.get('fp_contract') != label
                or report.get('fast_math') is not False):
            problems.append(f'{label}: incomplete or failed 8-case numerical/profile qualification')
    if off.get('simulator_sha256') != fast.get('simulator_sha256'):
        problems.append('different DUT binaries')
    if off.get('project_source_sha256') != fast.get('project_source_sha256'):
        problems.append('different project source content')
    for key in ('source_identity_sha256', 'compiler_version_sha256'):
        if off.get(key) != fast.get(key) or key not in off:
            problems.append(f'different or missing {key}')
    a = {r['name']: r for r in off['records']}
    b = {r['name']: r for r in fast['records']}
    for name in NAMES:
        x, y = a.get(name, {}), b.get(name, {})
        same = (x.get('fixture_sha256') == y.get('fixture_sha256')
                and x.get('fixture_header_sha256') == y.get('fixture_header_sha256')
                and x.get('fixture_sha256') is not None)
        if not same:
            problems.append(f'{name}: input/reference/tolerance identity mismatch')
        normalize = lambda cmd: [re.sub(r'/fma-comparison/(off|fast)/', '/fma-comparison/<mode>/',
                                       re.sub(r'^-ffp-contract=(off|fast)$', '-ffp-contract=<mode>', arg)) for arg in cmd]
        if (not x.get('target_build', {}).get('command')
                or normalize(x['target_build']['command']) != normalize(y.get('target_build', {}).get('command', []))):
            problems.append(f'{name}: build flags differ beyond contraction/output directory')
        xn, yn = x.get('dut_numeric', {}), y.get('dut_numeric', {})
        xp, yp = x.get('roi_profile', {}), y.get('roi_profile', {})
        xc, yc = xn.get('roi_cycles'), yn.get('roi_cycles')
        fused = lambda p: sum(p.get(k, 0) for k in ('fmadd_s', 'fmsub_s', 'fnmsub_s', 'fnmadd_s'))
        valid = same and x.get('passed') and y.get('passed') and bool(xc) and bool(yc)
        rows.append({'name': name, 'off_cycles': xc, 'fast_cycles': yc,
            'cycle_speedup_off_over_fast': xc / yc if valid else None,
            'off_retired': xp.get('retired'), 'fast_retired': yp.get('retired'),
            'off_fused_retired': fused(xp), 'fast_fused_retired': fused(yp),
            'off_max_absolute_error': xn.get('max_absolute_error'), 'fast_max_absolute_error': yn.get('max_absolute_error'),
            'off_max_tolerance_fraction': xn.get('max_tolerance_fraction'),
            'fast_max_tolerance_fraction': yn.get('max_tolerance_fraction'),
            'checksum_equal': xn.get('checksum') == yn.get('checksum'),
            'valid_pair': bool(valid)})
    if not all(r['valid_pair'] for r in rows):
        problems.append('one or more paired numerical results are invalid')
    return {'scope': 'Compiler contraction experiment on one RTL; diagnostic cycle ratios only, not architecture/PPA gains',
            'all_pairs_valid': not problems, 'problems': problems, 'results': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summarize-only', action='store_true')
    args = parser.parse_args()
    out = BASE / 'fma-comparison'
    out.mkdir(parents=True, exist_ok=True)
    if not args.summarize_only:
        (out / 'comparison.json').unlink(missing_ok=True)
        for mode in ('off', 'fast'):
            command = ['python3', 'scripts/qualify_fp_balanced.py', '--run-dut', '--profile-roi',
                       '--fp-contract', mode, '--out-dir', str(out / mode)]
            with (out / f'{mode}-invocation.log').open('w') as log:
                result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            print(f'{mode}: exit {result.returncode}', flush=True)
            if result.returncode:
                (out / 'comparison.json').write_text(json.dumps({
                    'scope': 'Failed contraction qualification; no performance ratios',
                    'all_pairs_valid': False,
                    'problems': [f'{mode}: qualification process exited {result.returncode}'],
                    'results': [],
                }, indent=2) + '\n')
                return 1
    off, fast = [json.loads((out / mode / 'summary.json').read_text()) for mode in ('off', 'fast')]
    report = compare(off, fast)
    for row, a, b in zip(report['results'], off['records'], fast['records']):
        if not row['valid_pair']:
            continue
        contents = []
        for record in (a, b):
            log = ROOT / record['dut']['log']
            if hashlib.sha256(log.read_bytes()).hexdigest() != record['dut'].get('log_sha256'):
                report['problems'].append(f"{row['name']}: raw DUT output changed after qualification")
                report['all_pairs_valid'] = False
            contents.append([int(x, 16) for x in re.findall(r'^FP DATA [0-9a-f]{8} ([0-9a-f]{8})$', log.read_text(), re.MULTILINE)])
        if len(contents[0]) != len(contents[1]):
            report['problems'].append(f"{row['name']}: output lengths differ")
            report['all_pairs_valid'] = False
            continue
        row['changed_output_words'] = sum(x != y for x, y in zip(*contents))
        decode = lambda word: struct.unpack('<f', struct.pack('<I', word))[0]
        row['max_absolute_off_fast_difference'] = max(abs(decode(x) - decode(y)) for x, y in zip(*contents))
    probe = json.loads((BASE / 'fma-finite/summary.json').read_text())
    if (not probe.get('all_passed') or probe.get('simulator_sha256') != off['simulator_sha256']
            or probe.get('fp_execute_sha256') != hashlib.sha256((ROOT / 'rtl/execute/fp/rv32_ooo_fp_execute.sv').read_bytes()).hexdigest()):
        report['problems'].append('exact finite FMA probe is failed or belongs to a different DUT')
        report['all_pairs_valid'] = False
    if report['all_pairs_valid']:
        speeds = [row['cycle_speedup_off_over_fast'] for row in report['results']]
        dsp = math.exp(sum(math.log(x) for x in speeds[:4]) / 4)
        matrix = math.exp(sum(math.log(x) for x in speeds[4:]) / 4)
        report['diagnostic_group_geomean'] = {'dsp': dsp, 'matrix_ml': matrix, 'fp32_equal_groups': math.sqrt(dsp * matrix)}
    (out / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    for row in report['results']:
        print(row['name'], row['off_cycles'], row['fast_cycles'], row['cycle_speedup_off_over_fast'], flush=True)
    for problem in report['problems']:
        print('INVALID:', problem)
    return 0 if report['all_pairs_valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
