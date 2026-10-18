#!/usr/bin/env python3
"""Audit executed/symbol text, approved defaults and prior stdout identities."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct

from fp_balanced_fixtures import NAMES

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'build/qualification/fp-balanced'
OUT = BASE / 'fma-bottleneck'
COMPARISON = BASE / 'fma-comparison'
OUTPUTS = ('assembly-audit.json', 'default-fast-audit.json', 'prior-qualification-audit.json')


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def section(path, name):
    data = path.read_bytes()
    require(data[:6] == b'\x7fELF\x01\x01', f'{path}: expected little-endian ELF32')
    offset = struct.unpack_from('<I', data, 32)[0]
    entry_size, count, string_index = struct.unpack_from('<HHH', data, 46)
    require(entry_size == 40 and string_index < count, f'{path}: invalid section table')
    headers = [struct.unpack_from('<10I', data, offset + i * entry_size) for i in range(count)]
    strings = headers[string_index]
    names = data[strings[4]:strings[4] + strings[5]]
    for header in headers:
        if names[header[0]:].split(b'\0', 1)[0].decode() == name:
            return header[3], data[header[4]:header[4] + header[5]]
    raise SystemExit(f'{path}: missing {name}')


def assembly_audit(summary):
    records = []
    for row in summary['records']:
        name, mode = row['name'], row['mode']
        directory = COMPARISON / mode / name
        elf, symbols = directory / 'rv32.elf', directory / 'rv32-symbols.elf'
        require(digest(elf) == row['elf_sha256'], f'{name}/{mode}: executed ELF identity changed')
        raw_profile = OUT / name / mode / 'core-profile.json'
        require(digest(raw_profile) == row['profile_sha256'], f'{name}/{mode}: profile changed')
        address, text = section(elf, '.text')
        require((address, text) == section(symbols, '.text'), f'{name}/{mode}: symbol/executed text differs')
        instructions, function = {}, ''
        for line in (directory / 'symbols-disassembly.log').read_text().splitlines():
            match = re.match(r'^([0-9a-f]+) <([^>]+)>:$', line)
            if match:
                function = match[2]
            match = re.match(r'^([0-9a-f]+):\s+([0-9a-f]{8})\s+(.+)$', line)
            if match:
                instructions[int(match[1], 16)] = {
                    'insn': match[2], 'assembly': match[3], 'function': function}
        pcs = []
        for pc in row['profile']['pcs']:
            location = int(pc['pc'], 16)
            require(address <= location <= address + len(text) - 4, f'{location:x}: outside executed text')
            word = struct.unpack_from('<I', text, location - address)[0]
            instruction = instructions[location]
            require(word == int(pc['insn'], 16) == int(instruction['insn'], 16),
                    f'{location:x}: observed/ELF/disassembly word differs')
            pcs.append(dict(pc, assembly=instruction['assembly'], function=instruction['function']))
        kernel = 'arm_fir_f32' if name == 'fir' else 'fp_kernel'
        snippet = [f'{pc:08x}: {v["insn"]} {v["assembly"]}'
                   for pc, v in sorted(instructions.items()) if v['function'] == kernel]
        require(snippet, f'{name}/{mode}: missing kernel symbol')
        snippet_path = OUT / name / mode / 'kernel-disassembly.txt'
        snippet_path.write_text('\n'.join(snippet) + '\n')
        records.append({'name': name, 'mode': mode, 'executed_elf_sha256': digest(elf),
                        'symbol_elf_sha256': digest(symbols), 'text_address': hex(address),
                        'text_sha256': hashlib.sha256(text).hexdigest(),
                        'symbol_and_executed_text_equal': True,
                        'all_observed_pcs_and_words_match_executed_text': True,
                        'kernel_disassembly': str(snippet_path.relative_to(ROOT)),
                        'kernel_disassembly_sha256': digest(snippet_path), 'pcs': pcs})
    return {'source_commit': summary['repository_commit'],
            'scope': 'Post-run read-only audit; source_commit is measured source; helper is pinned by hash',
            'audit_script_sha256': digest(Path(__file__)),
            'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
            'all_passed': True, 'records': records}


def complete_cases(report):
    return (report.get('all_passed') and report.get('passed_count') == 8
            and report.get('selected') == list(NAMES)
            and [row['name'] for row in report['records']] == list(NAMES))


def default_audit(source):
    default_path = BASE / 'baremetal-contract-fast/summary.json'
    explicit_path = COMPARISON / 'fast/summary.json'
    default, fast = read_json(default_path), read_json(explicit_path)
    require(complete_cases(default) and complete_cases(fast), 'Default/explicit fast needs all eight cases')
    require(default['fp_contract'] == 'fast' and default['fast_math'] is False, 'Wrong default FP policy')
    for key in ('simulator_sha256', 'source_identity_sha256', 'project_source_sha256'):
        require(default[key] == fast[key], f'Default fast differs in {key}')
    records = []
    for row, explicit in zip(default['records'], fast['records']):
        for key in ('fixture_sha256', 'fixture_header_sha256', 'elf_sha256', 'dut_numeric'):
            require(row[key] == explicit[key], f'{row["name"]}: default differs in {key}')
        command = row['target_build']['command']
        require('-ffp-contract=fast' in command and '-fno-fast-math' in command, 'Wrong default build flags')
        records.append({'name': row['name'], 'elf_sha256': row['elf_sha256'],
                        'fixture_sha256': row['fixture_sha256'],
                        'roi_cycles': row['dut_numeric']['roi_cycles'],
                        'numeric_checksum': row['dut_numeric']['checksum'],
                        'identical_to_explicit_fast': True})
    return {'source_commit': source, 'default_contract': 'fast', 'fast_math': False,
            'all_passed': True, 'default_summary_sha256': digest(default_path),
            'explicit_summary_sha256': digest(explicit_path), 'records': records}


def prior_audit():
    prior = ROOT / 'docs/evidence/2026-10-18/fma-contraction'
    records = []
    for mode in ('off', 'fast'):
        old, new = read_json(prior / mode / 'summary.json'), read_json(COMPARISON / mode / 'summary.json')
        require(complete_cases(old) and complete_cases(new), f'{mode}: incomplete prior/current case set')
        for previous, current in zip(old['records'], new['records']):
            for key in ('elf_sha256', 'dut_numeric', 'roi_profile'):
                require(previous[key] == current[key], f'{current["name"]}/{mode}: prior differs in {key}')
            require(previous['dut']['log_sha256'] == current['dut']['log_sha256'], 'Prior DUT stdout differs')
            require(digest(ROOT / current['dut']['log']) == current['dut']['log_sha256'], 'Current raw stdout changed')
            records.append({'name': current['name'], 'mode': mode, 'elf_sha256': current['elf_sha256'],
                            'dut_stdout_sha256': current['dut']['log_sha256'], 'byte_identical_to_prior': True})
    return {'all_passed': True,
            'scope': 'All 16 DUT stdout files and executed ELFs match the prior qualification',
            'previous_archive': '../fma-contraction', 'records': records}


def main():
    # Failure must not leave an old successful audit available to a later collector.
    for filename in OUTPUTS:
        (OUT / filename).unlink(missing_ok=True)
    summary = read_json(OUT / 'summary.json')
    expected = {(name, mode) for name in ('fir', 'bicg') for mode in ('off', 'fast')}
    require(summary['all_passed'] and len(summary['records']) == 4
            and {(r['name'], r['mode']) for r in summary['records']} == expected, 'Need four valid observed cases')
    reports = (assembly_audit(summary), default_audit(summary['repository_commit']), prior_audit())
    for filename, report in zip(OUTPUTS, reports):
        (OUT / filename).write_text(json.dumps(report, indent=2) + '\n')
    print('Artifact audits: assembly 4/4, implicit fast 8/8, prior ELF/stdout identity 16/16 PASS')


if __name__ == '__main__':
    main()
