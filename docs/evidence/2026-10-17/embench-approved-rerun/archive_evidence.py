"""Archive the completed clean-commit Embench rerun without large derived files."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'Makefile').is_file() and (p / 'scripts').is_dir())
RUN = ROOT / 'build/qualification/embench-approved-run'
BASE = ROOT / 'build/qualification/embench-fp-full'
DEST = ROOT / 'docs/evidence/2026-10-17/embench-approved-rerun'
PROFILE = 'rv32imf-zicsr-ilp32f'


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


context = read_json(RUN / 'run-context.json')
assert 'finished_at_utc' in context, 'Qualification is still running'
# No random delay was enabled or seed explicitly supplied for this run.
context['memory_model'].pop('seed', None)
context['memory_model']['random_seed'] = None
context['memory_model']['note'] += '; random delay disabled, no seed supplied'
context['warmup_heat'] = 1
context['cpu_mhz_scaling'] = 1
context['no_retire_limit'] = 10000
write_json(RUN / 'run-context.json', context)
summary = read_json(BASE / 'summary.json')
gate = read_json(BASE / 'dut-gate-report.json')
previous = read_json(ROOT / 'docs/evidence/2026-10-17/embench-dut-gate-report.json')
previous_by_name = {r['workload']: r for r in previous['results']}
assert summary['selected_count'] == 19 and gate['selected_count'] == 19
assert context['simulator_sha256_at_start'] == context['simulator_sha256_at_end']
assert gate['simulator_sha256'] == context['simulator_sha256_at_end']
assert context['working_tree_clean_at_start'] and context['working_tree_clean_at_end']
assert not DEST.exists(), 'Do not overwrite archived evidence'
DEST.mkdir(parents=True)
(DEST / 'dut-logs').mkdir()
write_json(DEST / 'run-context.json', context)
shutil.copy2(BASE / 'summary.json', DEST / 'embench-full-summary.json')
shutil.copy2(BASE / 'dut-gate-report.json', DEST / 'dut-gate-report.json')
for name in ('qualification.log', 'build-environment.log'):
    shutil.copy2(RUN / name, DEST / name)

other_logs, index, derived, binaries = {}, {}, [], []
entries = [*summary['metadata'].values()]
entries += [step for row in summary['records'] for step in row.values()
            if isinstance(step, dict) and 'log' in step]
for step in entries:
    original = step['log']
    path = ROOT / original
    if not path.is_file():
        index[original] = {'missing': True, 'returncode': step['returncode']}
        continue
    details = {'sha256': digest(path), 'bytes': path.stat().st_size}
    if path.name.endswith('.dis.log'):
        details['reason'] = 'Regenerate disassembly from the recorded build command and ELF hash'
        derived.append({'original_path': original, **details})
    elif path.name.endswith('.dut.log'):
        target = DEST / 'dut-logs' / path.name
        shutil.copy2(path, target)
        index[original] = {**details, 'archive_path': str(target.relative_to(DEST))}
    else:
        other_logs[original] = path.read_text()
        index[original] = {**details, 'archive_path': 'other-logs.json', 'key': original}

for row in summary['records']:
    if row['profile'] != PROFILE:
        continue
    name = row['benchmark']
    elf = BASE / f'{name}-{PROFILE}.elf'
    attrs = (ROOT / row['attributes']['log']).read_text()
    sizes = (ROOT / row['size']['log']).read_text().splitlines()[-1].split()
    arch = re.search(r'Tag_RISCV_arch: "([^"]+)"', attrs)
    matches = digest(elf) == row['elf_sha256']
    assert matches, f'{name}: ELF changed after qualification'
    binaries.append({
        'workload': name, 'elf_sha256_matches_summary': matches,
        'elf_sha256': row['elf_sha256'], 'isa': arch.group(1) if arch else None,
        'single_float_abi': 'single-float ABI' in attrs,
        'expected_isa': bool(arch and arch.group(1) == 'rv32i2p1_m2p0_f2p2_zicsr2p0_zmmul1p0'),
        'size_bytes': dict(zip(('text', 'data', 'bss'), map(int, sizes[:3]))),
    })
    derived.append({'original_path': str(elf.relative_to(ROOT)), 'sha256': digest(elf),
                    'bytes': elf.stat().st_size,
                    'reason': 'Regenerate ELF with the pinned toolchain and recorded build command'})
comparison = []
for row in gate['results']:
    old = previous_by_name[row['workload']]
    comparison.append({'workload': row['workload'],
                       'elf_sha256_matches': row['elf_sha256'] == old['elf_sha256'],
                       'metrics_match': row['metrics'] == old['metrics']})
write_json(DEST / 'other-logs.json', other_logs)
write_json(DEST / 'log-index.json', index)
write_json(DEST / 'regenerable-artifacts.json', derived)
write_json(DEST / 'binary-checks.json', {
    'scope': 'ELF architecture/ABI, hash and static section sizes; bss includes port reservations',
    'all_passed': len(binaries) == 19 and all(r['expected_isa'] and r['single_float_abi'] for r in binaries),
    'results': binaries})
write_json(DEST / 'reproducibility.json', {
    'scope': 'Compare identical diagnostic outputs; previous run was not from a clean source commit',
    'previous_report': '../embench-dut-gate-report.json',
    'all_match': all(r['elf_sha256_matches'] and r['metrics_match'] for r in comparison),
    'results': comparison})
shutil.copy2(Path(__file__), DEST / 'archive_evidence.py')
seconds = (datetime.fromisoformat(context['finished_at_utc']) - datetime.fromisoformat(context['started_at_utc'])).total_seconds()
lines = [
    '# Approved Embench 19-workload functional rerun', '',
    f"Source commit: `{context['repository_commit']}`; project and Embench trees were clean before and after execution.",
    f"Embench commit: `{context['embench_commit']}`.",
    f"UTC: {context['started_at_utc']} to {context['finished_at_utc']} ({seconds:.1f}s host wall time for the suite).", '',
    f"Functional gate: **{gate['passed_count']}/19**. Complete commands, stage results and ELF hashes are in [the summary](embench-full-summary.json).",
    'Each workload was built and self-checked natively, built for RV32IMF, run on Spike, and self-checked on the DUT.',
    'Self-checks use the upstream result checks and tolerances. This is not a full instruction-trace or FP-flag comparison.', '',
    'Conditions: `-std=gnu11 -O3 -march=rv32imf_zicsr -mabi=ilp32f`, `WARMUP_HEAT=1`, `CPU_MHZ=1` scaling.',
    'DUT defaults: 1 MiB RAM, data latency 1 cycle, random extra delay 0, no random seed supplied; 25,000,000-cycle / 180s per-program limits.',
    'The current DUT build does not enable Verilator assertions. Memory service, timing-window and physical contracts remain provisional.',
    'The CPU_MHZ scaling value does not establish an ASIC operating frequency.', '',
    'These are diagnostic cycles, not a frozen AP5B performance/PPA baseline or evidence of the 1.20x / 1.10x goals.', '',
    '| Workload | Native | Spike | DUT | Diagnostic ROI cycles |',
    '| --- | --- | --- | --- | ---: |',
]
for row in gate['results']:
    checks = row['checks']
    state = lambda value: 'PASS' if value else 'FAIL'
    lines.append(f"| `{row['workload']}` | {state(checks['native_self_check'])} | {state(checks['spike'])} | {state(checks['dut_self_check'])} | {row['metrics']['roi_cycles']:,} |")
lines += ['',
    '[Run context](run-context.json) records exact source, image IDs, simulator hash and command; [binary checks](binary-checks.json) verify the ELF ISA/ABI and hashes.',
    '[Gate report](dut-gate-report.json) keeps all 19 results. [Reproducibility comparison](reproducibility.json) checks ELF hashes and diagnostic metrics against the earlier run.',
    'Original DUT outputs are under [dut-logs](dut-logs/). Other original logs, including empty successful outputs, are stored by their runtime path in [other-logs.json](other-logs.json); [log-index.json](log-index.json) maps paths and hashes.',
    'Large ELFs and disassemblies remain regenerable; their identities and sizes are in [regenerable-artifacts.json](regenerable-artifacts.json).',
    'Raw size output includes port/runtime reservations and is not an application working-set measurement.', '',
    'Reproduce from the source commit above:', '', '```bash',
    'make check-fp-env sim-build JOBS=4', 'make qualify-embench-fp-dut JOBS=4',
    'make summarize-embench-fp-dut', '```', '',
    'After copying this directory, verify archived files with `sha256sum -c SHA256SUMS` from this directory.',
]
(DEST / 'README.md').write_text('\n'.join(lines) + '\n')
files = sorted(p for p in DEST.rglob('*') if p.is_file())
(DEST / 'SHA256SUMS').write_text(''.join(f'{digest(p)}  {p.relative_to(DEST)}\n' for p in files))
print(f'Archived {len(files) + 1} files to {DEST.relative_to(ROOT)}')
print(f"Functional: {gate['passed_count']}/19; ELF checks: {sum(r['expected_isa'] and r['single_float_abi'] for r in binaries)}/19; prior comparison: {all(r['elf_sha256_matches'] and r['metrics_match'] for r in comparison)}")
