#!/usr/bin/env python3
"""Recheck complete frozen A measurements without requiring B worktree RTL to be A."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').exists())
sys.path.insert(0, str(ROOT/'scripts'))
from baseline_contract import sha, validate
from experiment_provenance import review_provenance, measurement_command, retired_work
from measure_post_lsu_baseline import check_result
from review_cpu_experiment import geomean


def require(ok, message):
    if not ok:
        raise ValueError(message)


def review(measurement):
    experiment_path = ROOT/'experiments/lsu-a-v1/manifest.json'
    experiment = json.loads(experiment_path.read_text())
    baseline_path = ROOT/'baselines/ap5b-post-lsu-v1/manifest.json'
    baseline = json.loads(baseline_path.read_text())
    validate(baseline)
    require(sha(experiment_path) == 'a1782d1b5ac12cb7dbfba2900c9542693dad846b9af6f2e00f8e74d5fa0c758e'
            and sha(baseline_path) == experiment['baseline_manifest_sha256'], 'frozen contracts changed')
    report = json.loads((measurement/'summary.json').read_text())
    require(report['passed'] and report['start'] == report['end'] and not report['start']['status'],
            'clean completed measurement required')
    require(report['start']['commit'] == 'bf6702c6f4238aaf5f290356f3d0e0279f688f1e',
            'unexpected measurement source commit')
    sources = {**experiment['candidate_rtl_files_sha256'], **experiment['simulation_inputs_sha256'],
               **experiment['physical_inputs_sha256']}
    for name, digest in sources.items():
        data = subprocess.check_output(['git', 'show', report['start']['commit']+':'+name], cwd=ROOT)
        require(hashlib.sha256(data).hexdigest() == digest, 'measurement commit source differs: '+name)
    require(report['experiment_manifest_sha256'] == sha(experiment_path)
            and report['result_checker_sha256'] == sha(ROOT/'scripts/measure_post_lsu_baseline.py'),
            'measurement contract/checker changed')
    provenance, normal = review_provenance(experiment_path, experiment, report,
        ROOT/'build/experiments/lsu-a-v1/build-clean-v1/summary.json',
        ROOT/'build/experiments/lsu-a-v1/qualification-clean-v1/summary.json')
    period = report['core_period_ps']
    require(isinstance(period, int) and period > 2200 and period % 100 == 0
            and report['memory_ps'] == 10000, 'measurement period/memory policy changed')
    reference = ROOT/baseline['measurement']['formal_evidence']
    require(sha(reference/'summary.json') == report['baseline_summary_sha256']
            == baseline['measurement']['formal_summary_sha256'], 'baseline summary changed')
    old = {(r['family'], r['name']):r for r in json.loads((reference/'summary.json').read_text())['records']}
    rows = baseline['workloads']
    records = report['records']
    require(len(records) == 27 and [(r['family'], r['name']) for r in records]
            == [(r['family'], r['name']) for r in rows], 'complete ordered 27 workloads required')
    result = []
    checked = 0
    retained = ROOT/'build/experiments/lsu-a-v1/measurement-10000ps-v1'
    common_identical = []
    for row, record in zip(rows, records):
        directory = measurement/row['family']/row['name']
        profile, audit = directory/'profile.json', directory/'memory.json'
        measurement_command(record, normal, directory, period)
        require(record['passed'] and record['execution']['returncode'] == 0
                and sha(directory/'input.elf') == row['elf_sha256']
                and sha(directory/'dut.log') == record['execution']['log_sha256']
                and sha(profile) == record['profile_sha256'] and sha(audit) == record['memory_audit_sha256'],
                'changed raw measurement evidence')
        counters = json.loads(profile.read_text())
        check = check_result(row, (directory/'dut.log').read_text(), json.loads(audit.read_text()),
                             period, 10000, directory/'input.elf', counters, require_reference_cycles=False)
        previous = reference/row['family']/row['name']/'profile.json'
        require(sha(previous) == old[row['family'], row['name']]['profile_sha256'], 'baseline profile changed')
        original = json.loads(previous.read_text())
        require(not check['problems'] and counters['retired_classes'] == original['retired_classes']
                and retired_work(counters) == retired_work(original), 'numerical/memory/per-PC work differs')
        if check['numeric']:
            checked += check['numeric']['checked_values']
        before, after = row['reference_cycles']*10000, check['cycles']*period
        result.append(dict(family=row['family'], name=row['name'], group=row.get('group'),
                           baseline_cycles=row['reference_cycles'], candidate_cycles=check['cycles'],
                           baseline_time_ps=before, candidate_time_ps=after, time_speedup=before/after))
        if period == 10000:
            prior = retained/row['family']/row['name']
            identical = sha(profile) == sha(prior/'profile.json') and sha(audit) == sha(prior/'memory.json')
            require(identical, 'common-clock replay differs from retained A')
            common_identical.append(row['name'])
    require(checked == 3629, 'complete FP numerical denominator required')
    embedded = geomean([r['time_speedup'] for r in result if r['family'] == 'embench'])
    groups = {g:geomean([r['time_speedup'] for r in result if r['group'] == g]) for g in ['dsp', 'matrix_ml']}
    return dict(passed=True, scope='full A functional/cycle replay; new physical qualification remains separate',
                reviewer_sha256=sha(Path(__file__)), measurement=str(measurement.relative_to(ROOT)),
                measurement_summary_sha256=sha(measurement/'summary.json'), functional_provenance=provenance,
                source_commit=report['start']['commit'], source_files_verified=len(sources),
                period_ps=period, memory_ps=10000, per_pc_work_matches=True, numerical_values_checked=checked,
                common_clock_profiles_and_memory_identical=common_identical,
                embench_time_geomean_speedup=embedded, fp32_time_geomean_speedup=math.sqrt(math.prod(groups.values())),
                fp32_subgroup_speedup=groups, records=result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--measurement', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'preserve previous review')
    result = review(args.measurement.resolve())
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('records', 'common_clock_profiles_and_memory_identical')}, indent=2))


if __name__ == '__main__':
    main()
