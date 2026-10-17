#!/usr/bin/env python3
"""Numerically qualify all eight provisional FP32 cases; emits no suite score."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import struct
import subprocess
import time

from fp_balanced_fixtures import NAMES, fixture, write_header

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'build/qualification/fp-balanced'
CMSIS = BASE / 'CMSIS-DSP'
POLY = ROOT / 'build/qualification/polybench-c-4.2.1-beta'
SOURCES = {
    'fir': ('FilteringFunctions/arm_fir_f32.c', 'FilteringFunctions/arm_fir_init_f32.c'),
    'iir': ('FilteringFunctions/arm_biquad_cascade_df2T_f32.c', 'FilteringFunctions/arm_biquad_cascade_df2T_init_f32.c'),
    'pid': ('ControllerFunctions/arm_pid_init_f32.c',),
    'svm': ('SVMFunctions/arm_svm_linear_predict_f32.c', 'SVMFunctions/arm_svm_linear_init_f32.c'),
}
POLY_DIRS = {'gemm': 'linear-algebra/blas/gemm', 'bicg': 'linear-algebra/kernels/bicg',
             'cholesky': 'linear-algebra/solvers/cholesky'}
PASS = re.compile(r'FP BALANCED PASS name=(\w+) checksum=([0-9a-f]{8}) cycles=([0-9a-f]{8}) checked=([0-9a-f]{8})')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, log, timeout=120):
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, timeout=timeout)
        output, code = result.stdout, result.returncode
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or b''
        if isinstance(output, bytes):
            output = output.decode(errors='replace')
        output += f'\nTIMEOUT after {timeout}s\n'
        code = 124
    except OSError as exc:
        output, code = str(exc), 127
    log.write_text(output)
    return {'command': list(map(str, command)), 'returncode': code,
            'log': str(log.relative_to(ROOT)), 'log_sha256': digest(log),
            'wall_seconds': time.monotonic() - started}


def validate(case, log):
    text = log.read_text()
    match = PASS.search(text)
    rows = re.findall(r'^FP DATA ([0-9a-f]{8}) ([0-9a-f]{8})$', text, re.MULTILINE)
    expected = case['expected_double']
    if (not match or match[1] != case['name'] or len(rows) != len(expected)
            or int(match[4], 16) != len(expected)
            or [int(i, 16) for i, _ in rows] != list(range(len(expected)))):
        return {'passed': False, 'reason': 'Missing, duplicate or incomplete numerical output'}
    words = [int(v, 16) for _, v in rows]
    values = [struct.unpack('<f', struct.pack('<I', w))[0] for w in words]
    checksum = 2166136261
    for word in words:
        checksum = ((checksum ^ word) * 16777619) & 0xffffffff
    errors = [abs(x - y) for x, y in zip(values, expected)]
    limits = [case['absolute_tolerance'] + case['relative_tolerance'] * abs(y) for y in expected]
    bad = [i for i, (x, error, limit) in enumerate(zip(values, errors, limits))
           if not math.isfinite(x) or not error <= limit]
    result = {'passed': not bad and checksum == int(match[2], 16),
              'checked_values': len(values), 'failed_indices': bad,
              'checksum': match[2], 'checksum_verified': checksum == int(match[2], 16),
              'roi_cycles': int(match[3], 16),
              'max_absolute_error': max(errors) if all(math.isfinite(e) for e in errors) else None,
              'max_tolerance_fraction': max((e / lim for e, lim in zip(errors, limits)
                                              if lim > 0 and math.isfinite(e)), default=None)}
    if case['name'] in ('fir', 'iir'):
        half = len(values) // 2
        result['streaming_matches_whole_block_bits'] = words[:half] == words[half:]
    if case['name'] == 'cholesky':
        if not all(math.isfinite(x) for x in values):
            result.update(reconstruction_relative_inf_residual=None, positive_diagonal=False)
            return result
        n = case['dimensions']['n']
        a = case['arrays']['A']
        lower, index = [[0.0] * n for _ in range(n)], 0
        for i in range(n):
            for j in range(i + 1):
                lower[i][j] = values[index]
                index += 1
        residual = max(sum(abs(math.fsum(lower[i][k] * lower[j][k] for k in range(min(i, j) + 1))
                               - a[i * n + j]) for j in range(n)) for i in range(n))
        norm = max(sum(abs(x) for x in a[i * n:(i + 1) * n]) for i in range(n))
        result['reconstruction_relative_inf_residual'] = residual / norm
        result['positive_diagonal'] = all(lower[i][i] > 0 for i in range(n))
        result['passed'] &= (result['positive_diagonal'] and residual / norm
                             <= case['notes']['reconstruction_relative_inf_limit'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dut', action='store_true')
    parser.add_argument('--profile-roi', action='store_true',
                        help='Count retired instructions/FMA between the two RDCYCLE markers')
    parser.add_argument('--bench', choices=('all', *NAMES), default='all')
    parser.add_argument('--fp-contract', choices=('off', 'fast'), default='off',
                        help='Only control multiply-add contraction; fast-math remains disabled')
    parser.add_argument('--out-dir', type=Path,
                        help='Use a separate evidence directory for controlled experiments')
    args = parser.parse_args()
    if args.profile_roi and not args.run_dut:
        parser.error('--profile-roi requires --run-dut')
    out = (args.out_dir or BASE / ('baremetal' if args.fp_contract == 'off'
                                  else 'baremetal-contract-fast')).resolve()
    if not out.is_relative_to(ROOT):
        parser.error('--out-dir must be inside the repository workspace')
    out.mkdir(parents=True, exist_ok=True)
    path = out / ('summary.json' if args.bench == 'all' else f'summary-{args.bench}.json')
    path.unlink(missing_ok=True)
    source_check = run(['python3', 'scripts/prepare_fp_sources.py'], out / 'sources.log')
    if source_check['returncode']:
        parser.exit(1, f"Pinned source check failed; see {source_check['log']}\n")
    metadata = {}
    for key, command in {
        'repository': ['git', 'rev-parse', 'HEAD'],
        'working-tree': ['git', 'status', '--porcelain'],
        'native-gcc': ['gcc', '--version'],
        'riscv-gcc': ['riscv-none-elf-gcc', '--version'],
        'verilator': ['verilator', '--version'],
    }.items():
        metadata[key] = run(command, out / f'{key}.log')
    selected = NAMES if args.bench == 'all' else (args.bench,)
    report = {'scope': 'Provisional 4+4 numerical qualification; no score or frozen baseline',
              'started_at_utc': datetime.now(timezone.utc).isoformat(),
              'selected': selected, 'selected_count': len(selected), 'expected_count': 8,
              'run_dut': args.run_dut, 'source_check': source_check, 'metadata': metadata,
              'fp_contract': args.fp_contract, 'fast_math': False,
              'profile_roi': args.profile_roi,
              'source_identity_sha256': digest(BASE / 'source-summary.json'),
              'compiler_version_sha256': {name: digest(ROOT / metadata[name]['log'])
                                          for name in ('native-gcc', 'riscv-gcc')},
              'project_source_sha256': {p: digest(ROOT / p) for p in (
                  'scripts/qualify_fp_balanced.py', 'scripts/fp_balanced_fixtures.py',
                  'scripts/prepare_fp_sources.py', 'software/fp_bench/balanced.c',
                  'software/fp_bench/fft_alloc_guard.h', 'software/crt0/crt0.S',
                  'software/linker/link.ld', 'software/embench/fail_syscalls.c',
                  'rtl/execute/fp/rv32_ooo_fp_execute.sv', 'sim/tb/sim_main.cpp',
                  'sim/tb/fp_roi_profile.h')},
              'simulator_sha256': digest(ROOT / 'build/sim/rv32_ooo_sim') if args.run_dut else None,
              'records': []}
    for name in selected:
        directory = out / name
        directory.mkdir(exist_ok=True)
        try:
            case = fixture(name, CMSIS)
        except (OSError, ValueError, AssertionError) as exc:
            report['records'].append({'name': name, 'passed': False, 'fixture_error': str(exc)})
            print(f'{name:9s} FAIL fixture: {exc}', flush=True)
            path.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
            continue
        (directory / 'fixture.json').write_text(json.dumps(case, indent=2) + '\n')
        write_header(case, directory / 'fp_fixture.h')
        common = ['-std=gnu11', '-O3', '-fno-fast-math', f'-ffp-contract={args.fp_contract}',
                  '-ffunction-sections', '-fdata-sections', '-fstack-usage',
                  '-D__GNUC_PYTHON__', f'-DFP_CASE={NAMES.index(name)}',
                  f'-I{directory}', f'-I{CMSIS / "Include"}', f'-I{CMSIS / "PrivateInclude"}']
        sources = ['software/fp_bench/balanced.c']
        sources += [str(CMSIS / 'Source' / p) for p in SOURCES.get(name, ())]
        if name == 'fft':
            sources += [str(BASE / 'kissfft/kiss_fft.c')]
            # Upstream release logging option avoids linking stderr/newlib I/O.
            # Allocation attempts still set our fatal guard and every output is checked.
            common += [f'-I{BASE / "kissfft"}', '-DNDEBUG', '-DKISS_FFT_MALLOC=fp_fft_malloc',
                       '-DKISS_FFT_FREE=fp_fft_free', '-include', 'software/fp_bench/fft_alloc_guard.h']
        if name in POLY_DIRS:
            common += ['-DMINI_DATASET', '-DDATA_TYPE_IS_FLOAT', '-DPOLYBENCH_STACK_ARRAYS',
                       f'-I{POLY / "utilities"}', f'-I{POLY / POLY_DIRS[name]}']
        row = {'name': name, 'fixture_sha256': digest(directory / 'fixture.json'),
               'fixture_header_sha256': digest(directory / 'fp_fixture.h')}
        native, target = directory / 'native', directory / 'rv32.elf'
        native.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        row['native_build'] = run(['gcc', *common, '-DFP_BENCH_HOST', *sources,
                                   '-Wl,--gc-sections', '-o', str(native), '-lm'], directory / 'native-build.log')
        row['target_build'] = run(['riscv-none-elf-gcc', *common, '-march=rv32imf_zicsr', '-mabi=ilp32f',
            '-ffreestanding', '-nostartfiles', '-nostdlib', '-Isoftware/include',
            '-Tsoftware/linker/link.ld', 'software/crt0/crt0.S', 'software/embench/fail_syscalls.c',
            *sources, '-Wl,--gc-sections', '-o', str(target),
            '-Wl,--start-group', '-lm', '-lc', '-lgcc', '-Wl,--end-group'], directory / 'target-build.log')
        if row['native_build']['returncode'] == 0:
            row['native'] = run([str(native)], directory / 'native.log')
            row['native_numeric'] = validate(case, directory / 'native.log')
        if row['target_build']['returncode'] == 0:
            # Keep symbols for scoped instruction/call analysis; execute the
            # stripped copy with reproducible identity as before.
            symbols = directory / 'rv32-symbols.elf'
            shutil.copy2(target, symbols)
            row['symbol_disassembly'] = run(
                ['riscv-none-elf-objdump', '-d', str(symbols)], directory / 'symbols-disassembly.log')
            row['strip'] = run(['riscv-none-elf-strip', '--strip-unneeded', '--keep-symbol=tohost',
                                '--keep-symbol=fromhost', str(target)], directory / 'strip.log')
            row['elf_sha256'] = digest(target)
            for key, command in {
                'attributes': ['riscv-none-elf-readelf', '-h', '-A', str(target)],
                'size': ['riscv-none-elf-size', str(target)],
                'disassembly': ['riscv-none-elf-objdump', '-d', str(target)],
                'spike': ['spike', '--isa=rv32imf_zicsr', '-m0x80000000:0x100000,0x10000000:0x1000', str(target)],
            }.items():
                row[key] = run(command, directory / f'{key}.log')
            attrs = (directory / 'attributes.log').read_text()
            row['isa_abi_passed'] = ('rv32i2p1_m2p0_f2p2_zicsr2p0_zmmul1p0' in attrs
                                    and 'single-float ABI' in attrs)
            if args.run_dut:
                row['dut'] = run([str(ROOT / 'build/sim/rv32_ooo_sim'), f'+elf={target}',
                                   '+max-cycles=25000000', *(['+profile-fp-roi'] if args.profile_roi else [])], directory / 'dut.log', 180)
                row['dut_numeric'] = validate(case, directory / 'dut.log')
                row['dut_exit_passed'] = 'Exit status    : PASS (0)' in (directory / 'dut.log').read_text()
                if args.profile_roi:
                    found = re.search(r'^FP ROI cycle_reads=(\d+) retired=(\d+) fmadd_s=(\d+) fmsub_s=(\d+) fnmsub_s=(\d+) fnmadd_s=(\d+)$',
                                      (directory / 'dut.log').read_text(), re.MULTILINE)
                    row['roi_profile'] = dict(zip(('cycle_reads', 'retired', 'fmadd_s', 'fmsub_s', 'fnmsub_s', 'fnmadd_s'),
                                                   map(int, found.groups()))) if found else {}
                    row['roi_profile_passed'] = (row['roi_profile'].get('cycle_reads') == 2
                                                 and row['roi_profile'].get('retired', 0) > 0)
        required = ['native_build', 'target_build', 'native', 'strip', 'attributes', 'size', 'disassembly', 'spike']
        if args.run_dut:
            required.append('dut')
        row['passed'] = (all(row.get(k, {}).get('returncode') == 0 for k in required)
                         and row.get('native_numeric', {}).get('passed') is True
                         and row.get('isa_abi_passed') is True
                         and (not args.run_dut or (row.get('dut_numeric', {}).get('passed') is True
                                                   and row.get('dut_exit_passed') is True)))
        row['passed'] &= not args.profile_roi or row.get('roi_profile_passed') is True
        report['records'].append(row)
        path.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        print(f"{name:9s} {'PASS' if row['passed'] else 'FAIL'} "
              f"native={row.get('native_numeric', {}).get('passed')} "
              f"DUT={row.get('dut_numeric', {}).get('passed')} "
              f"ROI={row.get('dut_numeric', {}).get('roi_cycles')}", flush=True)
    report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    report['passed_count'] = sum(r['passed'] for r in report['records'])
    report['all_passed'] = (all(r['returncode'] == 0 for r in metadata.values())
                            and report['passed_count'] == len(selected))
    path.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(f"FP32 qualification: {report['passed_count']}/{len(selected)}; {path.relative_to(ROOT)}")
    return 0 if report['all_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
