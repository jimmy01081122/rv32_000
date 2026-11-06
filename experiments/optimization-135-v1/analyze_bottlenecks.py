#!/usr/bin/env python3
"""Reconcile retained full-suite wait positions and instruction-count limits."""
import argparse
import collections
import csv
import json
import math
from pathlib import Path
import subprocess

import analyze_retained as retained

ROOT = Path(__file__).resolve().parents[2]


def geomean(values):
    return math.exp(sum(map(math.log, values)) / len(values))


def integer_class(insn):
    if insn & 127 == 0x33 and insn >> 25 == 1:
        return 'div_rem' if (insn >> 12) & 7 >= 4 else 'multiply'
    return 'other'


def analyze():
    # Use the latest fresh A replay, with the same verified model/workload bytes.
    retained.MEASUREMENTS['A'] = ('build/experiments/optimization-135-v1/'
                                'measurement-source/build/measurement-10000ps-v1')
    references = {
        'A': ('docs/evidence/2026-11-05/optimization-135-A/common-clock-review.json',
              '8c149aafffe5d6f32a1c1c4ffc37cb96be942f748a1ffbe593f01b7a878a339f'),
        'B': ('build/experiments/lsu-b-validation-v2/final-common-clock-review.json',
              'c133e45ff7ad30f1ad049a13a45f4c66b3c8a6d37e6cad85daa8aee397de0ea0'),
    }
    sources = {}
    for variant, (name, expected) in references.items():
        path = ROOT / name
        retained.require(retained.sha(path) == expected, 'accepted review changed')
        review = json.loads(path.read_text())
        retained.require(review['passed'], 'unqualified reference')
        score = review['measurement'] if variant == 'B' else review
        summary = ROOT / retained.MEASUREMENTS[variant] / 'summary.json'
        retained.require(retained.sha(summary) == score['measurement_summary_sha256'],
                         'measurement differs from accepted review')
        sources[name] = expected
    manifest = ROOT / 'baselines/ap5b-post-lsu-v1/manifest.json'
    retained.require(retained.sha(manifest) ==
                     '60f59b3cc705560885e2101046d810cf3548fef277c1c1e5820826ef25485fb6',
                     'frozen baseline changed')
    baseline = json.loads(manifest.read_text())
    retained.require(retained.sha(ROOT / retained.MEASUREMENTS['baseline'] / 'summary.json')
                     == baseline['measurement']['formal_summary_sha256'], 'baseline summary changed')
    checked = retained.retained(ROOT)
    sources.update({str(Path(p).relative_to(ROOT)): h for p, h in checked['sources_sha256'].items()})
    groups = {(r['family'], r['name']): r.get('group') for r in baseline['workloads']}
    original = {}
    rows = []
    for row in checked['records']:
        key = (row['family'], row['name'])
        profile_path = ROOT / retained.MEASUREMENTS[row['variant']] / Path(*key) / 'profile.json'
        profile = json.loads(profile_path.read_text())
        partition = profile['cycle_partition']
        instructions = sum(profile['retired_classes'].values()) + partition.get('retired_marker', 0)
        retained.require(instructions == partition.get('retired_body', 0) +
                         partition.get('retired_marker', 0), 'retirement denominator differs')
        if row['variant'] == 'baseline':
            original[key] = (row['cycles'], instructions)
        retained.require(instructions == original[key][1], 'retired instruction work differs')
        integer_waits = collections.Counter()
        integer_pcs = []
        for pc in profile['pcs']:
            if pc['kind'] == 'integer_other':
                kind = integer_class(int(pc['insn'], 16))
                integer_waits[kind] += pc['head_wait']
                integer_pcs.append(dict(pc, decoded_integer_class=kind))
        # PC head waits can have broader scope in general. Only admit this split
        # where the sum actually reconciles to the mutually exclusive bucket.
        retained.require(sum(integer_waits.values()) == partition.get('head_wait_integer_other', 0),
                         'per-PC integer waits do not reconcile to exclusive cycle bucket')
        store = profile['store_ack_wait_phases']
        load = profile['load_head_wait_phases']
        retained.require(sum(store.values()) == partition.get('store_ack_wait', 0), 'store phases differ')
        retained.require(sum(load.values()) == partition.get('head_wait_int_load', 0) +
                         partition.get('head_wait_fp_load', 0), 'load phases differ')
        cycles = row['cycles']
        rows.append(dict(row, group=groups[key], instructions_including_closing_marker=instructions,
                         retirement_ipc=instructions / cycles,
                         partition_percent={k: 100 * v / cycles for k, v in partition.items()},
                         store_ack_wait_phases=store, load_head_wait_phases=load,
                         integer_head_wait_split=dict(integer_waits),
                         integer_div_rem_head_wait_percent=100 * integer_waits['div_rem'] / cycles,
                         own_load_response_buffer_percent=100 * load.get('own_response_buffer', 0) / cycles,
                         top_integer_wait_pcs=sorted(integer_pcs, key=lambda p: -p['head_wait'])[:5],
                         speedup_vs_original=original[key][0] / cycles,
                         ideal_one_retire_per_cycle_speedup_vs_original=original[key][0] / instructions,
                         ideal_one_retire_per_cycle_speedup_vs_current=cycles / instructions))
    summary = {}
    for variant in retained.MEASUREMENTS:
        subset = [r for r in rows if r['variant'] == variant]
        summary[variant] = {}
        for label, field in [('measured', 'speedup_vs_original'),
                             ('ideal_single_retirement', 'ideal_one_retire_per_cycle_speedup_vs_original')]:
            embedded = geomean([r[field] for r in subset if r['family'] == 'embench'])
            fp = math.sqrt(math.prod(geomean([r[field] for r in subset if r['group'] == group])
                                     for group in ('dsp', 'matrix_ml')))
            summary[variant][label] = dict(embench=embedded, fp32=fp)
    for name in ['sim/tb/core_roi_profile.h', 'rtl/execute/int/rv32_ooo_divider.sv',
                 'rtl/core/rv32_ooo_core.sv', 'rtl/lsu/rv32_ooo_lsu.sv',
                 'rtl/issue/rv32_ooo_fp_iq.sv', 'rtl/rob/rv32_ooo_rob.sv']:
        sources[name] = retained.sha(ROOT / name)
    return dict(passed=True, scope='read-only reanalysis of 81 accepted profiles; no new benchmark or RTL',
                source_parent_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                analyzer_sha256=retained.sha(Path(__file__)),
                reused_validator_sha256=retained.sha(Path(retained.__file__)),
                cpu_period_ps=10000, memory_ps=10000, sources_sha256=sources,
                interpretation=['Wait buckets identify blocked retirement positions, not proven causal unit latency or removable cycles.',
                                'Overlapping events and entry-cycle counters cannot be added to the cycle partition.',
                                'Ideal single-retirement bound assumes unchanged architectural instruction count, 100 MHz and zero stalls; it is unattainable in general and not a forecast.'],
                integer_split_reconciles_cases=len(rows), scores=summary, records=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze()
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    fields = ['variant', 'family', 'name', 'cycles', 'retirement_ipc', 'speedup_vs_original',
              'integer_div_rem_head_wait_percent', 'own_load_response_buffer_percent']
    with (args.output / 'workloads.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(result['records'])
    print(json.dumps(dict(passed=True, profiles=len(result['records']), scores=result['scores']), indent=2))
