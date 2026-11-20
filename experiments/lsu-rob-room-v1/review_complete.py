#!/usr/bin/env python3
"""Join independently reviewed ROB-space timing, area and complete workload evidence."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').is_file())
BASE = ROOT/'build/experiments/lsu-rob-room-v1'
HERE = ROOT/'experiments/lsu-rob-room-v1'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

def module(name):
    spec = importlib.util.spec_from_file_location('room_'+name, HERE/(name+'.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    output = parser.parse_args().output
    require(not output.exists(), 'fresh complete review required')
    physical = module('review_physical').review(BASE/'native/physical-ROOM-v4/guard/independent-boundary-v1')
    require(physical == json.loads((BASE/'physical-review.json').read_text()), 'repeated physical review differs')
    native = physical['ROOM_physical']
    fastest = native['smallest_tested_passing_period_ps']
    scores = {}
    measure = module('review_measurement')
    for name, period in [('common_clock', 10000), ('fastest_tested', fastest)]:
        score = measure.review(BASE/f'measurement-{period}ps-v1')
        require(score['period_ps'] == period and period in native['qualified_periods_ps'], 'unqualified workload period')
        score['planning_targets'] = dict(
            embench_geomean_ge_1_20=score['embench_time_geomean_speedup'] >= 1.20,
            fp32_geomean_ge_1_20=score['fp32_time_geomean_speedup'] >= 1.20,
            original_area_ratio_le_1_10=physical['original_area_ratio'] <= 1.10)
        score['all_planning_targets_met'] = all(score['planning_targets'].values())
        scores[name] = score
    parent_path = BASE/'parent-comparison.json'
    parent = json.loads(parent_path.read_text())
    require(parent['passed'] and parent['reviews']['candidate'] == measure.review(BASE/'measurement-10000ps-v1'),
            'functional parent comparison uses different candidate evidence')
    for path, digest in parent['source_sha256'].items():
        require(sha(ROOT/path) == digest, 'parent comparison raw evidence changed')
    old_path = ROOT/'build/experiments/lsu-ab-v1/physical-review.json'
    index = json.loads((ROOT/'docs/evidence/2026-11-13/lsu-ab-complete/copy-inventory.json').read_text())
    entry = next(r for r in index['records'] if r['source'] == str(old_path.relative_to(ROOT)))
    require(sha(old_path) == entry['sha256'], 'archived A+B physical reference changed')
    old = json.loads(old_path.read_text())
    require(old['passed'], 'A+B physical reference failed')
    result = dict(passed=True,
        scope='ROB-space candidate at the common global-route research boundary; original baseline unchanged',
        reviewer_sha256=sha(Path(__file__)), physical_review_sha256=sha(BASE/'physical-review.json'),
        physical=physical, operating_points=scores, parent_comparison_sha256=sha(parent_path),
        common_clock_relative_to_parents=parent['relative_to'],
        AB_physical_review_sha256=sha(old_path),
        area_relative_to_AB=native['standard_cell_area_um2']/old['AB_physical']['standard_cell_area_um2'],
        AB_smallest_tested_passing_period_ps=old['AB_physical']['smallest_tested_passing_period_ps'],
        all_planning_targets_met_at_any_tested_point=any(s['all_planning_targets_met'] for s in scores.values()))
    output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(passed=True, fastest_tested_period_ps=fastest,
        area_ratio=physical['original_area_ratio'], area_relative_to_AB=result['area_relative_to_AB'],
        scores={k:{q:v[q] for q in ['period_ps','embench_time_geomean_speedup',
                                   'fp32_time_geomean_speedup','all_planning_targets_met']} for k,v in scores.items()}), indent=2))

if __name__ == '__main__':
    main()
