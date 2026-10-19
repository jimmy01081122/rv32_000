#!/usr/bin/env python3
"""Exact finite FMA results/flags vs an integer oracle, Spike and the DUT."""
import hashlib
import argparse
import json
from pathlib import Path
import subprocess

from fma_reference import vectors
from qualify_fp_balanced import ROOT, BASE, run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sim',type=Path,default=ROOT/'build/sim/rv32_ooo_sim')
    parser.add_argument('--out',type=Path,default=BASE/'fma-finite')
    args=parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(ROOT/'build'):parser.error('output must be under build/')
    out.mkdir(parents=True, exist_ok=True)
    data = vectors()
    (out / 'vectors.json').write_text(json.dumps({'finite_inputs_only': True, 'seed': '0x464d4132',
                                                'count': len(data), 'vectors': data}, indent=2) + '\n')
    (out / 'fma_vectors.h').write_text(f'#define FMA_VECTOR_COUNT {len(data)}u\nstatic const uint32_t fma_vectors[][7] = {{\n'
        + ''.join('  {' + ', '.join(f'0x{x:08x}u' for x in row) + '},\n' for row in data) + '};\n')
    report = {'scope': 'Finite operands only; exact value and all five fflags bits, four FMA opcodes, five rounding modes',
              'vector_count': len(data), 'simulator_sha256': hashlib.sha256(args.sim.read_bytes()).hexdigest(),
              'fp_execute_sha256': hashlib.sha256((ROOT / 'rtl/execute/fp/rv32_ooo_fp_execute.sv').read_bytes()).hexdigest(),
              'repository_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'oracle_sha256': hashlib.sha256((ROOT / 'scripts/fma_reference.py').read_bytes()).hexdigest(), 'records': []}
    for name, source in (('rounding', 'fma_rounding_probe.c'), ('finite', 'fma_exact_vectors.c')):
        elf = out / f'{name}.elf'
        elf.unlink(missing_ok=True)
        row = {'name': name}
        row['build'] = run(['riscv-none-elf-gcc', '-std=gnu11', '-O3', '-ffp-contract=off', '-fno-fast-math',
            '-march=rv32imf_zicsr', '-mabi=ilp32f', '-ffreestanding', '-nostartfiles', '-nostdlib',
            '-Isoftware/include', f'-I{out}', '-Tsoftware/linker/link.ld', 'software/crt0/crt0.S',
            f'software/fp_bench/{source}', '-o', str(elf), '-lgcc'], out / f'{name}-build.log')
        if row['build']['returncode'] == 0:
            row['elf_sha256'] = hashlib.sha256(elf.read_bytes()).hexdigest()
            row['spike'] = run(['spike', '--isa=rv32imf_zicsr', '-m0x80000000:0x100000,0x10000000:0x1000', str(elf)],
                               out / f'{name}-spike.log')
            row['dut'] = run([str(args.sim), f'+elf={elf}', '+max-cycles=25000000'],
                             out / f'{name}-dut.log', 180)
            text = (out / f'{name}-dut.log').read_text()
            row['dut_self_check'] = ('FMA ROUNDING PROBE PASS' if name == 'rounding'
                                      else f'FMA VECTORS PASS count={len(data):08x} failures=00000000') in text
        row['passed'] = (all(row.get(k, {}).get('returncode') == 0 for k in ('build', 'spike', 'dut'))
                         and row.get('dut_self_check') is True)
        report['records'].append(row)
        print(f"FMA {name}: {'PASS' if row['passed'] else 'FAIL'}", flush=True)
    report['all_passed'] = all(r['passed'] for r in report['records'])
    (out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['all_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
