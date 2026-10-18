#!/usr/bin/env python3
"""Fail-closed ready throttling and precise access-fault tests (not performance)."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sim', type=Path, default=Path('build/sim-assert/rv32_ooo_sim'))
    parser.add_argument('--out', type=Path, default=Path('build/qualification/lsu-interface'))
    args = parser.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    records = []

    def run(name, command, check):
        try:
            result = subprocess.run(list(map(str, command)), cwd=ROOT, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            code, text = result.returncode, result.stdout
        except OSError as exc:
            code, text = 127, str(exc)
        except subprocess.TimeoutExpired as exc:
            code, text = 124, (exc.stdout or b'').decode(errors='replace')
        log = out / (name + '.log')
        log.write_text(text)
        passed = code == 0 and 'PASS (0)' in text and check(text)
        records.append(dict(name=name, command=list(map(str, command)), returncode=code,
                            passed=passed, log=str(log), log_sha256=sha(log)))
        print(name, 'PASS' if passed else 'FAIL', flush=True)

    # Normal programs have no traps; load/store forwarding and redirect/flush are covered.
    for name in ('store_forwarding', 'rv32i_basic', 'lsu_redirect_variable_lat',
                 'partial_overlap', 'unresolved_store', 'wrong_path_store'):
        elf = Path('build/tests') / (name + '.elf')
        for delay in (1, 4):
            command = [args.sim, f'+elf={elf}', '+dmem-ready-period=4',
                       f'+dmem-latency={delay}', '+max-cycles=1000000']
            run(f'{name}-ready4-delay{delay}', command,
                lambda text: 'TRAP encountered' not in text and
                bool(re.search(r'DMEM ENV blocked_load_cycles=[1-9][0-9]*', text)))

    # Check exact PC, cause, tval, one delivered fault, no retirement of fault or
    # younger instructions. Firmware also checks CSRs, register rollback, absence
    # of younger memory side effects, unchanged failed write, and post-MRET memory.
    for case, name in enumerate(('sw', 'sb', 'sh', 'fsw', 'lw', 'flw')):
        elf = out / (name + '.elf')
        command = ['riscv-none-elf-gcc', '-march=rv32imf_zicsr', '-mabi=ilp32f',
                   '-nostdlib', '-nostartfiles', '-Wl,--no-relax',
                   '-Tsoftware/linker/link.ld', f'-DCASE={case}',
                   'software/interface/lsu_fault.S', '-o', elf]
        build = subprocess.run(list(map(str, command)), cwd=ROOT, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (out / (name + '-build.log')).write_text(build.stdout)
        if build.returncode:
            raise RuntimeError(build.stdout)
        nm = subprocess.check_output(['riscv-none-elf-nm', str(elf)], text=True)
        symbols = {label: int(addr, 16) for addr, _, label in
                   (line.split() for line in nm.splitlines() if len(line.split()) == 3)}
        offset = {1: 1, 2: 2}.get(case, 0)
        addr, pc = symbols['fault_word'] + offset, symbols['fault_pc']
        cause = 5 if case >= 4 else 7
        bad_pcs = {pc, symbols['younger_register_pc'], symbols['younger_store_pc']}
        for period in (1, 4):
            for delay in (1, 2, 4):
                label = f'{name}-ready{period}-delay{delay}'
                trace = out / (label + '.trace')
                # Remove stale output before invoking the simulator.
                trace.unlink(missing_ok=True)
                command = [args.sim, f'+elf={elf}', f'+trace={trace}',
                           f'+dmem-ready-period={period}', f'+dmem-latency={delay}',
                           f'+dmem-fault-{"load" if case >= 4 else "store"}=0x{addr & ~3:x}',
                           '+max-cycles=100000']

                def check(text):
                    traps = re.findall(r'TRAP encountered.*PC=0x([0-9a-f]+).*cause=0x([0-9a-f]+) tval=0x([0-9a-f]+)', text)
                    pcs = [int(x, 16) for x in re.findall(r'^core 0: 0x([0-9a-f]+)',
                                                        trace.read_text() if trace.exists() else '', re.MULTILINE)]
                    return (traps == [(f'{pc:x}', f'{cause:x}', f'{addr:x}')] and
                            'fault_requests=1 fault_responses=1' in text and
                            not (set(pcs) & bad_pcs) and pcs.count(symbols['resume']) == 1 and
                            pcs.count(symbols['handler']) == 1)
                run(label, command, check)
                records[-1].update(elf_sha256=sha(elf), expected_pc=pc,
                                   expected_cause=cause, expected_tval=addr,
                                   trace=str(trace), trace_sha256=sha(trace) if trace.exists() else None)
    passed = len(records) == 48 and all(row['passed'] for row in records)
    report = dict(scope='Interface correctness only; assertions enabled by caller',
                  simulator=str(args.sim), simulator_sha256=sha(args.sim),
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  tracked_dirty=bool(subprocess.check_output(['git', 'status', '--porcelain', '-uno'])),
                  expected_count=48, passed=passed, records=records)
    (out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
