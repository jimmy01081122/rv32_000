#!/usr/bin/env python3
"""Profile a fixed representative set at three memory delays before LSU selection."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess

from qualify_fp_balanced import ROOT, BASE, digest, run, validate

OUT = ROOT / 'build/qualification/lsu-review'
EMBENCH = ('crc32', 'matmult-int', 'wikisort', 'minver')
FP32 = ('fir', 'bicg')
CASES = (*EMBENCH, *FP32)
LATENCIES = (1, 2, 4)
EVIDENCE = ROOT / 'docs/evidence/2026-10-18'


def read_json(path):
    return json.loads(path.read_text())


def strip_observer(text):
    return re.sub(r'^FP ROI .*\n', '', text, flags=re.MULTILINE)


def check_observation(profile, text, family, case=None, expected_checksum=None):
    problems = []
    if 'Exit status    : PASS (0)' not in text:
        problems.append('DUT program self-check/exit failed')
    marker = re.search(r'^FP ROI cycle_reads=(\d+) retired=(\d+)', text, re.MULTILINE)
    if not marker or int(marker[1]) != 2:
        problems.append('expected exactly two low RDCYCLE markers')
    if family == 'embench':
        elapsed = re.search(r'\[Embench\] Benchmark executed in cycles: (\d+)', text)
        cycles = int(elapsed[1]) if elapsed else None
        numeric = None
    else:
        # Reuse the unchanged independent numeric gate through a log-shaped input.
        class Output:
            def read_text(self):
                return text
        numeric = validate(case, Output())
        cycles = numeric.get('roi_cycles')
        if not numeric.get('passed') or numeric.get('checksum') != expected_checksum:
            problems.append('FP32 numerical outputs/checksum differ')
    if not cycles or cycles != profile['cycles']:
        problems.append('CSR ROI and observed commit-window cycles differ')
    parts = profile['cycle_partition']
    retired = sum(profile['retired_classes'].values())
    if sum(parts.values()) != profile['cycles'] or parts.get('retired_body') != retired:
        problems.append('incomplete cycle/retired partition')
    if not marker or int(marker[2]) != retired or parts.get('retired_marker') != 1:
        problems.append('retired histogram or closing marker differs')
    if profile['trace_mismatches'] or profile['layout_mismatches']:
        problems.append('trace or packed-layout consistency failed')
    if sum(profile['store_ack_wait_phases'].values()) != parts.get('store_ack_wait', 0):
        problems.append('store phases do not cover store-ack waits')
    load_wait = sum(parts.get(key, 0) for key in ('head_wait_int_load', 'head_wait_fp_load'))
    if sum(profile['load_head_wait_phases'].values()) != load_wait:
        problems.append('load phases do not cover load-head waits')
    return {'roi_cycles': cycles, 'numeric': numeric, 'problems': problems}


def inputs():
    epath = EVIDENCE / 'fma-contraction/embench/summary.json'
    gpath = EVIDENCE / 'fma-contraction/embench/dut-gate-report.json'
    fpath = EVIDENCE / 'fma-bottleneck/default-fast/summary.json'
    embench, gate, fp = read_json(epath), read_json(gpath), read_json(fpath)
    if not gate['all_passed'] or gate['passed_count'] != 19 or not fp['all_passed'] or fp['passed_count'] != 8:
        raise SystemExit('Need complete archived Embench19 and FP32 qualifications')
    if fp['fp_contract'] != 'fast' or fp['fast_math'] is not False:
        raise SystemExit('FP32 inputs must use the approved fast policy')
    result = {}
    for name in EMBENCH:
        record = next(r for r in embench['records'] if r['benchmark'] == name and r['profile'] == 'rv32imf-zicsr-ilp32f')
        result[name] = {'family': 'embench', 'elf': ROOT / f'build/qualification/embench-fp-full/{name}-rv32imf-zicsr-ilp32f.elf',
                        'elf_sha256': record['elf_sha256'], 'record': record,
                        'previous_stdout': EVIDENCE / f'fma-contraction/raw/embench/{name}-rv32imf-zicsr-ilp32f.dut.txt'}
    for name in FP32:
        record = next(r for r in fp['records'] if r['name'] == name)
        directory = BASE / 'baremetal-contract-fast' / name
        fixture = directory / 'fixture.json'
        if digest(fixture) != record['fixture_sha256']:
            raise SystemExit(f'{name}: fixture identity differs from the archived qualification')
        result[name] = {'family': 'fp32', 'elf': directory / 'rv32.elf',
                        'elf_sha256': record['elf_sha256'], 'record': record,
                        'fixture': read_json(fixture), 'fixture_sha256': digest(fixture),
                        'previous_stdout': ROOT / record['dut']['log']}
    for name, item in result.items():
        if not item['elf'].is_file() or digest(item['elf']) != item['elf_sha256']:
            raise SystemExit(f'{name}: missing/changed ELF; prepare the qualified embench-fp-full and baremetal-contract-fast outputs')
    return result, {str(p.relative_to(ROOT)): digest(p) for p in (epath, gpath, fpath)}


def summarize(records, selected, latencies):
    expected = {(name, latency) for name in selected for latency in latencies}
    keys = [(row['name'], row['latency']) for row in records]
    problems, rows = [], []
    if len(keys) != len(expected) or set(keys) != expected:
        problems.append('missing, duplicate or unexpected case/latency records')
    if not all(row.get('passed') for row in records):
        problems.append('one or more functional/profile gates failed')
    for name in selected:
        matching = {r['latency']: r for r in records if r['name'] == name}
        if 1 not in matching or not matching[1].get('passed'):
            problems.append(f'{name}: valid nominal reference missing')
            continue
        baseline = matching[1]
        for latency in latencies:
            item = matching.get(latency)
            if not item or not item.get('passed'):
                continue
            if item['profile']['retired_classes'] != baseline['profile']['retired_classes']:
                problems.append(f'{name}/{latency}: architectural instruction mix changed')
            cycles = item['profile']['cycles']
            rows.append({'name': name, 'family': item['family'], 'latency': latency,
                         'roi_cycles': cycles, 'slowdown_vs_latency1': cycles / baseline['profile']['cycles'],
                         'retired': sum(item['profile']['retired_classes'].values()),
                         'store_ack_wait': item['profile']['cycle_partition'].get('store_ack_wait', 0),
                         'own_load_response_wait': item['profile']['load_head_wait_phases'].get('own_response_buffer', 0)})
    # Ratios describe memory-model sensitivity of unchanged RTL, never a CPU gain.
    return {'all_passed': not problems, 'problems': problems, 'rows': rows,
            'scope': 'Per-case sensitivity of unchanged RTL; no subset benchmark score or candidate CPU speedup'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=('all', *CASES), default='all')
    parser.add_argument('--latencies', nargs='+', choices=LATENCIES, type=int, default=list(LATENCIES))
    parser.add_argument('--out-dir', type=Path, default=OUT)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if not out.is_relative_to(ROOT) or len(set(args.latencies)) != len(args.latencies) or 1 not in args.latencies:
        parser.error('use a workspace output directory, unique delays, and include nominal delay 1')
    out.mkdir(parents=True, exist_ok=True)
    destination = out / 'summary.json'
    destination.unlink(missing_ok=True)
    source, qualifications = inputs()
    selected = CASES if args.case == 'all' else (args.case,)
    simulator = ROOT / 'build/sim/rv32_ooo_sim'
    if subprocess.run(['git', 'diff', '--quiet', '5065e7f', '--', 'rtl', 'sim'], cwd=ROOT).returncode:
        raise SystemExit('RTL/simulator differs from the qualified observer; review and requalify it first')
    report = {'scope': 'Diagnostic representative workloads for LSU candidate selection; full suite targets unchanged',
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'started_at_utc': datetime.now(timezone.utc).isoformat(),
              'working_tree_clean_at_start': not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip(),
              'simulator_sha256': digest(simulator), 'qualification_sha256': qualifications,
              'script_sha256': digest(Path(__file__)), 'selected': selected, 'latencies': args.latencies,
              'memory_model': {'ram_bytes': 1048576, 'configured_response_delay_cycles': args.latencies,
                               'random_extra_delay_cycles': 0}, 'records': [], 'all_passed': False}
    destination.write_text(json.dumps(report, indent=2) + '\n')
    for name in selected:
        item = source[name]
        for latency in args.latencies:
            directory = out / name / f'latency-{latency}'
            directory.mkdir(parents=True, exist_ok=True)
            profile_path = directory / 'core-profile.json'
            profile_path.unlink(missing_ok=True)
            record = {'name': name, 'family': item['family'], 'latency': latency,
                      'elf_sha256': item['elf_sha256'], 'problems': []}
            command = [str(simulator), f'+elf={item["elf"]}', '+max-cycles=100000000',
                       f'+dmem-latency={latency}', '+dmem-rand-delay=0']
            record['observed'] = run([*command, f'+profile-core-roi={profile_path}'], directory / 'observed.log', 600)
            text = (directory / 'observed.log').read_text()
            if record['observed']['returncode'] == 0 and profile_path.exists():
                record['profile'] = read_json(profile_path)
                record['profile_sha256'] = digest(profile_path)
                check = check_observation(record['profile'], text, item['family'], item.get('fixture'),
                                          item['record'].get('dut_numeric', {}).get('checksum'))
                record.update(check)
            else:
                record['problems'].append('observed execution failed/timed out or profile missing')
            if latency == 1:
                record['unobserved'] = run(command, directory / 'unobserved.log', 600)
                plain = (directory / 'unobserved.log').read_text()
                record['observer_invariant'] = strip_observer(text) == plain
                previous = item['previous_stdout'].read_text()
                record['matches_qualified_stdout'] = plain == strip_observer(previous)
                if record['unobserved']['returncode'] or not record['observer_invariant'] or not record['matches_qualified_stdout']:
                    record['problems'].append('nominal observer/qualified-model invariance failed')
            record['passed'] = not record['problems']
            report['records'].append(record)
            destination.write_text(json.dumps(report, indent=2) + '\n')
            print(name, latency, 'PASS' if record['passed'] else record['problems'], flush=True)
    report['sensitivity'] = summarize(report['records'], selected, args.latencies)
    report['all_passed'] = report['sensitivity']['all_passed']
    report['complete_fixed_study'] = (report['all_passed'] and selected == CASES
                                      and tuple(args.latencies) == LATENCIES)
    report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    report['working_tree_clean_at_end'] = not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()
    destination.write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['all_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
